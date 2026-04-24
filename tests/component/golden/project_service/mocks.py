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
        self._files: Dict[str, Dict[str, Any]] = {}
        self._should_fail: Optional[Exception] = None

    def set_failure(self, error: Exception):
        self._should_fail = error

    def clear_failure(self):
        self._should_fail = None

    def seed_project(
        self, project_id: str, user_id: str, name: str, **kwargs
    ) -> Dict[str, Any]:
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

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str = None,
        custom_instructions: str = None,
    ) -> Dict[str, Any]:
        if self._should_fail:
            raise self._should_fail
        project_id = str(uuid.uuid4())
        now = datetime.now(tz=timezone.utc)
        project = {
            "id": project_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "custom_instructions": custom_instructions,
            "created_at": now,
            "updated_at": now,
        }
        self._projects[project_id] = project
        return project

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        if self._should_fail:
            raise self._should_fail
        return self._projects.get(project_id)

    async def list_projects(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        if self._should_fail:
            raise self._should_fail
        user_projects = [p for p in self._projects.values() if p["user_id"] == user_id]
        user_projects.sort(key=lambda p: p["updated_at"], reverse=True)
        return user_projects[offset : offset + limit]

    async def update_project(
        self, project_id: str, **updates
    ) -> Optional[Dict[str, Any]]:
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

    async def create_project_file(
        self,
        project_id: str,
        file_id: str,
        filename: str,
        storage_path: str,
        file_type: str = None,
        file_size: int = None,
    ) -> Dict[str, Any]:
        if self._should_fail:
            raise self._should_fail
        now = datetime.now(tz=timezone.utc)
        record = {
            "id": file_id,
            "project_id": project_id,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "storage_path": storage_path,
            "created_at": now,
        }
        self._files[file_id] = record
        return record

    async def list_project_files(
        self, project_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        if self._should_fail:
            raise self._should_fail
        files = [f for f in self._files.values() if f["project_id"] == project_id]
        files.sort(key=lambda f: f["created_at"], reverse=True)
        return files[offset : offset + limit]

    async def get_project_file(
        self, project_id: str, file_id: str
    ) -> Optional[Dict[str, Any]]:
        if self._should_fail:
            raise self._should_fail
        project_file = self._files.get(file_id)
        if not project_file or project_file["project_id"] != project_id:
            return None
        return project_file

    async def delete_project_file(self, project_id: str, file_id: str) -> bool:
        if self._should_fail:
            raise self._should_fail
        project_file = self._files.get(file_id)
        if not project_file or project_file["project_id"] != project_id:
            return False
        del self._files[file_id]
        return True

    async def cleanup(self) -> None:
        pass


class MockStorageServiceClient:
    """Mock storage client for project file component testing."""

    def __init__(self):
        self.should_fail_upload = False
        self.upload_result: Optional[Dict[str, Any]] = None
        self.delete_result = True

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        user_id: str,
        organization_id: Optional[str] = None,
        access_level: str = "private",
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        auto_delete_after_days: Optional[int] = None,
        enable_indexing: bool = True,
    ) -> Optional[Dict[str, Any]]:
        if self.should_fail_upload:
            return None
        if self.upload_result is not None:
            return self.upload_result
        return {
            "file_id": str(uuid.uuid4()),
            "file_path": f"storage/{filename}",
            "file_size": len(file_content),
            "content_type": content_type or "application/octet-stream",
        }

    async def delete_file(
        self,
        file_id: str,
        user_id: str,
        permanent: bool = False,
    ) -> bool:
        return self.delete_result
