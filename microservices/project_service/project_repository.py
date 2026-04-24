"""Project Repository — PostgreSQL data access (#258, #295, #296, #298)"""
import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

from .protocols import RepositoryError

logger = logging.getLogger(__name__)


class ProjectRepository:
    def __init__(self, config_manager: ConfigManager):
        self.schema = "project"
        self.table = "projects"
        self.files_table = "project_files"
        pg_config = config_manager.get_service_connection("postgres")
        self.db = AsyncPostgresClient(
            host=pg_config["host"],
            port=pg_config["port"],
            database=pg_config["database"],
            user=pg_config["user"],
            password=pg_config["password"],
            schema=self.schema,
        )

    async def create_project(self, user_id: str, name: str, description: str = None, custom_instructions: str = None) -> Dict[str, Any]:
        project_id = str(uuid.uuid4())
        now = datetime.now(tz=timezone.utc)
        try:
            async with self.db:
                await self.db.execute(
                    f"INSERT INTO {self.schema}.{self.table} (id, user_id, name, description, custom_instructions, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    params=[project_id, user_id, name, description, custom_instructions, now, now]
                )
        except Exception as e:
            raise RepositoryError("Failed to create project", cause=e) from e
        return {"id": project_id, "user_id": user_id, "name": name, "description": description, "custom_instructions": custom_instructions, "created_at": now, "updated_at": now}

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with self.db:
                rows = await self.db.query(f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1", params=[project_id])
            return dict(rows[0]) if rows else None
        except Exception as e:
            raise RepositoryError("Failed to fetch project", cause=e) from e

    async def list_projects(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            async with self.db:
                rows = await self.db.query(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE user_id = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
                    params=[user_id, limit, offset]
                )
            return [dict(r) for r in (rows or [])]
        except Exception as e:
            raise RepositoryError("Failed to list projects", cause=e) from e

    async def update_project(self, project_id: str, **updates) -> Optional[Dict[str, Any]]:
        updates["updated_at"] = datetime.now(tz=timezone.utc)
        set_clauses = []
        params = []
        for i, (k, v) in enumerate(updates.items(), 1):
            set_clauses.append(f"{k} = ${i}")
            params.append(v)
        params.append(project_id)
        try:
            async with self.db:
                await self.db.execute(
                    f"UPDATE {self.schema}.{self.table} SET {', '.join(set_clauses)} WHERE id = ${len(params)}",
                    params=params
                )
            return await self.get_project(project_id)
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError("Failed to update project", cause=e) from e

    async def delete_project(self, project_id: str) -> bool:
        try:
            async with self.db:
                await self.db.execute(f"DELETE FROM {self.schema}.{self.table} WHERE id = $1", params=[project_id])
            return True
        except Exception as e:
            raise RepositoryError("Failed to delete project", cause=e) from e

    async def set_instructions(self, project_id: str, instructions: str) -> bool:
        return bool(await self.update_project(project_id, custom_instructions=instructions))

    async def count_projects(self, user_id: str) -> int:
        try:
            async with self.db:
                rows = await self.db.query(f"SELECT COUNT(*) as cnt FROM {self.schema}.{self.table} WHERE user_id = $1", params=[user_id])
            return rows[0]["cnt"] if rows else 0
        except Exception as e:
            raise RepositoryError("Failed to count projects", cause=e) from e

    async def create_project_file(
        self,
        project_id: str,
        file_id: str,
        filename: str,
        storage_path: str,
        file_type: str = None,
        file_size: int = None,
    ) -> Dict[str, Any]:
        now = datetime.now(tz=timezone.utc)
        try:
            async with self.db:
                await self.db.execute(
                    f"INSERT INTO {self.schema}.{self.files_table} (id, project_id, filename, file_type, file_size, storage_path, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    params=[file_id, project_id, filename, file_type, file_size, storage_path, now],
                )
        except Exception as e:
            raise RepositoryError("Failed to create project file", cause=e) from e
        return {
            "id": file_id,
            "project_id": project_id,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "storage_path": storage_path,
            "created_at": now,
        }

    async def list_project_files(
        self,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        try:
            async with self.db:
                rows = await self.db.query(
                    f"SELECT * FROM {self.schema}.{self.files_table} WHERE project_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                    params=[project_id, limit, offset],
                )
            return [dict(r) for r in (rows or [])]
        except Exception as e:
            raise RepositoryError("Failed to list project files", cause=e) from e

    async def get_project_file(
        self,
        project_id: str,
        file_id: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            async with self.db:
                rows = await self.db.query(
                    f"SELECT * FROM {self.schema}.{self.files_table} WHERE project_id = $1 AND id = $2",
                    params=[project_id, file_id],
                )
            return dict(rows[0]) if rows else None
        except Exception as e:
            raise RepositoryError("Failed to fetch project file", cause=e) from e

    async def delete_project_file(self, project_id: str, file_id: str) -> bool:
        try:
            async with self.db:
                await self.db.execute(
                    f"DELETE FROM {self.schema}.{self.files_table} WHERE project_id = $1 AND id = $2",
                    params=[project_id, file_id],
                )
            return True
        except Exception as e:
            raise RepositoryError("Failed to delete project file", cause=e) from e

    async def cleanup(self) -> None:
        pass
