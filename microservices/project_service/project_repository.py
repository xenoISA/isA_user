"""Project Repository — PostgreSQL data access (#258, #295, #296, #298)"""

import logging
import os
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
        self._tables_initialized = False
        host, port = config_manager.discover_service(
            service_name="postgres_service",
            default_host="localhost",
            default_port=5432,
            env_host_key="POSTGRES_HOST",
            env_port_key="POSTGRES_PORT",
        )
        self.db = AsyncPostgresClient(
            host=host,
            port=port,
            database=os.getenv("POSTGRES_DB", "isa_platform"),
            username=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            user_id="project_service",
            min_pool_size=1,
            max_pool_size=2,
        )

    async def initialize(self) -> None:
        await self._ensure_tables()

    async def _ensure_tables(self) -> None:
        if self._tables_initialized:
            return

        create_schema_sql = f"CREATE SCHEMA IF NOT EXISTS {self.schema}"
        create_projects_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.{self.table} (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                org_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                custom_instructions TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """
        create_projects_user_idx_sql = (
            f"CREATE INDEX IF NOT EXISTS idx_{self.table}_user_id "
            f"ON {self.schema}.{self.table}(user_id)"
        )
        create_projects_updated_idx_sql = (
            f"CREATE INDEX IF NOT EXISTS idx_{self.table}_updated_at "
            f"ON {self.schema}.{self.table}(updated_at DESC)"
        )
        create_project_files_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.{self.files_table} (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES {self.schema}.{self.table}(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                file_type TEXT,
                file_size BIGINT,
                storage_path TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """
        create_project_files_project_idx_sql = (
            f"CREATE INDEX IF NOT EXISTS idx_{self.files_table}_project_id "
            f"ON {self.schema}.{self.files_table}(project_id)"
        )
        create_project_files_created_idx_sql = (
            f"CREATE INDEX IF NOT EXISTS idx_{self.files_table}_created_at "
            f"ON {self.schema}.{self.files_table}(created_at DESC)"
        )

        try:
            async with self.db:
                await self.db.execute(create_schema_sql)
                await self.db.execute(create_projects_table_sql)
                await self.db.execute(create_projects_user_idx_sql)
                await self.db.execute(create_projects_updated_idx_sql)
                await self.db.execute(create_project_files_table_sql)
                await self.db.execute(create_project_files_project_idx_sql)
                await self.db.execute(create_project_files_created_idx_sql)
        except Exception as e:
            raise RepositoryError("Failed to initialize project tables", cause=e) from e

        self._tables_initialized = True

    @staticmethod
    def _require_query_result(rows: Optional[List[Dict[str, Any]]], operation: str) -> List[Dict[str, Any]]:
        if rows is None:
            raise RepositoryError(f"Failed to {operation}")
        return rows

    @staticmethod
    def _require_rows_affected(rows_affected: Optional[int], operation: str) -> None:
        if rows_affected is None or rows_affected < 1:
            raise RepositoryError(f"Failed to {operation}")

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str = None,
        custom_instructions: str = None,
    ) -> Dict[str, Any]:
        await self._ensure_tables()
        project_id = str(uuid.uuid4())
        now = datetime.now(tz=timezone.utc)
        try:
            async with self.db:
                rows_affected = await self.db.execute(
                    f"INSERT INTO {self.schema}.{self.table} (id, user_id, name, description, custom_instructions, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    params=[
                        project_id,
                        user_id,
                        name,
                        description,
                        custom_instructions,
                        now,
                        now,
                    ],
                )
            self._require_rows_affected(rows_affected, "create project")
        except Exception as e:
            raise RepositoryError("Failed to create project", cause=e) from e
        return {
            "id": project_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "custom_instructions": custom_instructions,
            "created_at": now,
            "updated_at": now,
        }

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        await self._ensure_tables()
        try:
            async with self.db:
                rows = await self.db.query(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1",
                    params=[project_id],
                )
            rows = self._require_query_result(rows, "fetch project")
            return dict(rows[0]) if rows else None
        except Exception as e:
            raise RepositoryError("Failed to fetch project", cause=e) from e

    async def list_projects(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        await self._ensure_tables()
        try:
            async with self.db:
                rows = await self.db.query(
                    f"SELECT * FROM {self.schema}.{self.table} WHERE user_id = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
                    params=[user_id, limit, offset],
                )
            rows = self._require_query_result(rows, "list projects")
            return [dict(r) for r in rows]
        except Exception as e:
            raise RepositoryError("Failed to list projects", cause=e) from e

    async def update_project(
        self, project_id: str, **updates
    ) -> Optional[Dict[str, Any]]:
        await self._ensure_tables()
        updates["updated_at"] = datetime.now(tz=timezone.utc)
        set_clauses = []
        params = []
        for i, (k, v) in enumerate(updates.items(), 1):
            set_clauses.append(f"{k} = ${i}")
            params.append(v)
        params.append(project_id)
        try:
            async with self.db:
                rows_affected = await self.db.execute(
                    f"UPDATE {self.schema}.{self.table} SET {', '.join(set_clauses)} WHERE id = ${len(params)}",
                    params=params,
                )
            self._require_rows_affected(rows_affected, "update project")
            return await self.get_project(project_id)
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError("Failed to update project", cause=e) from e

    async def delete_project(self, project_id: str) -> bool:
        await self._ensure_tables()
        try:
            async with self.db:
                rows_affected = await self.db.execute(
                    f"DELETE FROM {self.schema}.{self.table} WHERE id = $1",
                    params=[project_id],
                )
            self._require_rows_affected(rows_affected, "delete project")
            return True
        except Exception as e:
            raise RepositoryError("Failed to delete project", cause=e) from e

    async def set_instructions(self, project_id: str, instructions: str) -> bool:
        return bool(
            await self.update_project(project_id, custom_instructions=instructions)
        )

    async def count_projects(self, user_id: str) -> int:
        await self._ensure_tables()
        try:
            async with self.db:
                rows = await self.db.query(
                    f"SELECT COUNT(*) as cnt FROM {self.schema}.{self.table} WHERE user_id = $1",
                    params=[user_id],
                )
            rows = self._require_query_result(rows, "count projects")
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
        await self._ensure_tables()
        now = datetime.now(tz=timezone.utc)
        try:
            async with self.db:
                rows_affected = await self.db.execute(
                    f"INSERT INTO {self.schema}.{self.files_table} (id, project_id, filename, file_type, file_size, storage_path, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    params=[
                        file_id,
                        project_id,
                        filename,
                        file_type,
                        file_size,
                        storage_path,
                        now,
                    ],
                )
            self._require_rows_affected(rows_affected, "create project file")
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
        await self._ensure_tables()
        try:
            async with self.db:
                rows = await self.db.query(
                    f"SELECT * FROM {self.schema}.{self.files_table} WHERE project_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                    params=[project_id, limit, offset],
                )
            rows = self._require_query_result(rows, "list project files")
            return [dict(r) for r in rows]
        except Exception as e:
            raise RepositoryError("Failed to list project files", cause=e) from e

    async def get_project_file(
        self,
        project_id: str,
        file_id: str,
    ) -> Optional[Dict[str, Any]]:
        await self._ensure_tables()
        try:
            async with self.db:
                rows = await self.db.query(
                    f"SELECT * FROM {self.schema}.{self.files_table} WHERE project_id = $1 AND id = $2",
                    params=[project_id, file_id],
                )
            rows = self._require_query_result(rows, "fetch project file")
            return dict(rows[0]) if rows else None
        except Exception as e:
            raise RepositoryError("Failed to fetch project file", cause=e) from e

    async def delete_project_file(self, project_id: str, file_id: str) -> bool:
        await self._ensure_tables()
        try:
            async with self.db:
                rows_affected = await self.db.execute(
                    f"DELETE FROM {self.schema}.{self.files_table} WHERE project_id = $1 AND id = $2",
                    params=[project_id, file_id],
                )
            self._require_rows_affected(rows_affected, "delete project file")
            return True
        except Exception as e:
            raise RepositoryError("Failed to delete project file", cause=e) from e

    async def cleanup(self) -> None:
        pass
