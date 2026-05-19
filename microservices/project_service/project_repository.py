"""Project Repository — PostgreSQL data access (#258, #295, #296, #298)"""

import logging
import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

from .protocols import RepositoryError


from core.postgres_client import compute_pool_size as _pg_compute_pool


def _pg_max_pool() -> int:
    """Per-pod Postgres max pool size; scales with replica count (epic #345/#346)."""
    return _pg_compute_pool()


def _pg_min_pool() -> int:
    """Per-pod Postgres min pool size; small constant to avoid pinning idle connections."""
    return 2 if _pg_max_pool() >= 4 else 1


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
            min_pool_size=_pg_min_pool(),
            max_pool_size=_pg_max_pool(),
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
                owner_id TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                description TEXT,
                custom_instructions TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                starred_at TIMESTAMPTZ NULL,
                archived_at TIMESTAMPTZ NULL
            )
        """
        add_projects_org_id_sql = f"ALTER TABLE {self.schema}.{self.table} ADD COLUMN IF NOT EXISTS org_id TEXT"
        add_projects_owner_id_sql = f"ALTER TABLE {self.schema}.{self.table} ADD COLUMN IF NOT EXISTS owner_id TEXT NOT NULL DEFAULT ''"
        add_projects_starred_at_sql = f"ALTER TABLE {self.schema}.{self.table} ADD COLUMN IF NOT EXISTS starred_at TIMESTAMPTZ NULL"
        add_projects_archived_at_sql = f"ALTER TABLE {self.schema}.{self.table} ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ NULL"
        create_projects_user_idx_sql = f"CREATE INDEX IF NOT EXISTS idx_{self.table}_user_id ON {self.schema}.{self.table}(user_id)"
        create_projects_org_idx_sql = f"CREATE INDEX IF NOT EXISTS idx_{self.table}_org_id ON {self.schema}.{self.table}(org_id)"
        create_projects_updated_idx_sql = f"CREATE INDEX IF NOT EXISTS idx_{self.table}_updated_at ON {self.schema}.{self.table}(updated_at DESC)"
        create_projects_owner_id_idx_sql = f"CREATE INDEX IF NOT EXISTS idx_project_projects_owner_id ON {self.schema}.{self.table}(owner_id)"
        create_projects_owner_active_idx_sql = (
            f"CREATE INDEX IF NOT EXISTS idx_project_projects_owner_active "
            f"ON {self.schema}.{self.table}(owner_id) WHERE archived_at IS NULL"
        )
        create_projects_starred_idx_sql = (
            f"CREATE INDEX IF NOT EXISTS idx_project_projects_starred "
            f"ON {self.schema}.{self.table}(starred_at) WHERE starred_at IS NOT NULL"
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
                await self.db.execute(add_projects_org_id_sql)
                await self.db.execute(add_projects_owner_id_sql)
                await self.db.execute(add_projects_starred_at_sql)
                await self.db.execute(add_projects_archived_at_sql)
                await self.db.execute(create_projects_user_idx_sql)
                await self.db.execute(create_projects_org_idx_sql)
                await self.db.execute(create_projects_updated_idx_sql)
                await self.db.execute(create_projects_owner_id_idx_sql)
                await self.db.execute(create_projects_owner_active_idx_sql)
                await self.db.execute(create_projects_starred_idx_sql)
                await self.db.execute(create_project_files_table_sql)
                await self.db.execute(create_project_files_project_idx_sql)
                await self.db.execute(create_project_files_created_idx_sql)
        except Exception as e:
            raise RepositoryError("Failed to initialize project tables", cause=e) from e

        self._tables_initialized = True

    @staticmethod
    def _require_query_result(
        rows: Optional[List[Dict[str, Any]]], operation: str
    ) -> List[Dict[str, Any]]:
        if rows is None:
            raise RepositoryError(f"Failed to {operation}")
        return rows

    @staticmethod
    def _require_rows_affected(rows_affected: Optional[int], operation: str) -> None:
        if rows_affected is None or rows_affected < 1:
            raise RepositoryError(f"Failed to {operation}")

    @staticmethod
    def _shape_project(row: Dict[str, Any]) -> Dict[str, Any]:
        project = dict(row)
        project["organization_id"] = project.get("org_id")
        return project

    async def create_project(
        self,
        user_id: str,
        name: str,
        description: str = None,
        custom_instructions: str = None,
        organization_id: str = None,
        owner_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        await self._ensure_tables()
        project_id = str(uuid.uuid4())
        now = datetime.now(tz=timezone.utc)
        effective_owner = owner_id or user_id
        try:
            async with self.db:
                rows_affected = await self.db.execute(
                    f"INSERT INTO {self.schema}.{self.table} (id, user_id, org_id, owner_id, name, description, custom_instructions, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                    params=[
                        project_id,
                        user_id,
                        organization_id,
                        effective_owner,
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
            "org_id": organization_id,
            "organization_id": organization_id,
            "owner_id": effective_owner,
            "name": name,
            "description": description,
            "custom_instructions": custom_instructions,
            "created_at": now,
            "updated_at": now,
            "starred_at": None,
            "archived_at": None,
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
            return self._shape_project(rows[0]) if rows else None
        except Exception as e:
            raise RepositoryError("Failed to fetch project", cause=e) from e

    async def list_projects(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        organization_id: str = None,
        include_archived: bool = False,
        starred_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """List projects scoped to user/org.

        Filters added in story #442 (see xenoISA/isA_#429 §15.3/§15.6):
        - include_archived=False (default) hides rows with archived_at set.
        - starred_only=True restricts to rows with starred_at set.
        """
        await self._ensure_tables()
        if organization_id:
            base_clause = "org_id = $1"
            params: List[Any] = [organization_id]
        else:
            base_clause = "user_id = $1"
            params = [user_id]

        filters: List[str] = []
        if not include_archived:
            filters.append("archived_at IS NULL")
        if starred_only:
            filters.append("starred_at IS NOT NULL")

        where_sql = base_clause
        if filters:
            where_sql = f"{base_clause} AND " + " AND ".join(filters)

        order_clause = (
            "starred_at DESC NULLS LAST, updated_at DESC"
            if starred_only
            else "updated_at DESC"
        )

        params.extend([limit, offset])
        limit_idx = len(params) - 1
        offset_idx = len(params)

        sql = (
            f"SELECT * FROM {self.schema}.{self.table} "
            f"WHERE {where_sql} "
            f"ORDER BY {order_clause} "
            f"LIMIT ${limit_idx} OFFSET ${offset_idx}"
        )

        try:
            async with self.db:
                rows = await self.db.query(sql, params=params)
            rows = self._require_query_result(rows, "list projects")
            return [self._shape_project(r) for r in rows]
        except Exception as e:
            raise RepositoryError("Failed to list projects", cause=e) from e

    async def list_projects_for_export(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        organization_id: str = None,
    ) -> List[Dict[str, Any]]:
        """List all subject-owned projects for GDPR export.

        This deliberately keeps archived projects and scopes organization
        filters to the subject owner instead of exporting the whole org.
        """
        await self._ensure_tables()
        where_sql = "(user_id = $1 OR owner_id = $1)"
        params: List[Any] = [user_id]
        if organization_id:
            params.append(organization_id)
            where_sql = f"{where_sql} AND org_id = ${len(params)}"

        params.extend([limit, offset])
        limit_idx = len(params) - 1
        offset_idx = len(params)

        sql = (
            f"SELECT * FROM {self.schema}.{self.table} "
            f"WHERE {where_sql} "
            "ORDER BY updated_at DESC "
            f"LIMIT ${limit_idx} OFFSET ${offset_idx}"
        )

        try:
            async with self.db:
                rows = await self.db.query(sql, params=params)
            rows = self._require_query_result(rows, "list projects for export")
            return [self._shape_project(r) for r in rows]
        except Exception as e:
            raise RepositoryError("Failed to list projects for export", cause=e) from e

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

    # ── Star / Archive (#442, see xenoISA/isA_#429 §15.3, §15.6) ─────────

    async def set_starred(
        self, project_id: str, starred: bool
    ) -> Optional[Dict[str, Any]]:
        """Set or clear starred_at for a project. Returns the updated project."""
        await self._ensure_tables()
        now = datetime.now(tz=timezone.utc) if starred else None
        try:
            async with self.db:
                rows_affected = await self.db.execute(
                    f"UPDATE {self.schema}.{self.table} SET starred_at = $1, updated_at = $2 WHERE id = $3",
                    params=[now, datetime.now(tz=timezone.utc), project_id],
                )
            self._require_rows_affected(rows_affected, "update starred flag")
            return await self.get_project(project_id)
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError("Failed to update starred flag", cause=e) from e

    async def set_archived(
        self, project_id: str, archived: bool
    ) -> Optional[Dict[str, Any]]:
        """Set or clear archived_at for a project. Returns the updated project."""
        await self._ensure_tables()
        now = datetime.now(tz=timezone.utc) if archived else None
        try:
            async with self.db:
                rows_affected = await self.db.execute(
                    f"UPDATE {self.schema}.{self.table} SET archived_at = $1, updated_at = $2 WHERE id = $3",
                    params=[now, datetime.now(tz=timezone.utc), project_id],
                )
            self._require_rows_affected(rows_affected, "update archived flag")
            return await self.get_project(project_id)
        except RepositoryError:
            raise
        except Exception as e:
            raise RepositoryError("Failed to update archived flag", cause=e) from e

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
