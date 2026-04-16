"""Project Repository — PostgreSQL data access (#258)"""
import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from isa_common import AsyncPostgresClient
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class ProjectNotFoundError(Exception):
    pass

class ProjectRepository:
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.schema = "project"
        self.table = "projects"
        self.files_table = "project_files"
        self.config_manager = config_manager or ConfigManager("project_service")
        pg_config = self.config_manager.get_service_connection("postgres")
        self.db = AsyncPostgresClient(
            host=pg_config.get("host", "localhost"),
            port=pg_config.get("port", 5432),
            database=pg_config.get("database", "isa_user"),
            user=pg_config.get("user", "postgres"),
            password=pg_config.get("password", ""),
            schema=self.schema,
        )

    async def create_project(self, user_id: str, name: str, description: str = None, custom_instructions: str = None) -> Dict[str, Any]:
        project_id = str(uuid.uuid4())
        now = datetime.now(tz=timezone.utc)
        async with self.db:
            await self.db.execute(
                f"INSERT INTO {self.schema}.{self.table} (id, user_id, name, description, custom_instructions, created_at, updated_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                params=[project_id, user_id, name, description, custom_instructions, now, now]
            )
        return {"id": project_id, "user_id": user_id, "name": name, "description": description, "custom_instructions": custom_instructions, "created_at": now, "updated_at": now}

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        async with self.db:
            rows = await self.db.fetch(f"SELECT * FROM {self.schema}.{self.table} WHERE id = $1", params=[project_id])
        return dict(rows[0]) if rows else None

    async def list_projects(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        async with self.db:
            rows = await self.db.fetch(
                f"SELECT * FROM {self.schema}.{self.table} WHERE user_id = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
                params=[user_id, limit, offset]
            )
        return [dict(r) for r in rows]

    async def update_project(self, project_id: str, **updates) -> Optional[Dict[str, Any]]:
        updates["updated_at"] = datetime.now(tz=timezone.utc)
        set_clauses = []
        params = []
        for i, (k, v) in enumerate(updates.items(), 1):
            set_clauses.append(f"{k} = ${i}")
            params.append(v)
        params.append(project_id)
        async with self.db:
            await self.db.execute(
                f"UPDATE {self.schema}.{self.table} SET {', '.join(set_clauses)} WHERE id = ${len(params)}",
                params=params
            )
        return await self.get_project(project_id)

    async def delete_project(self, project_id: str) -> bool:
        async with self.db:
            result = await self.db.execute(f"DELETE FROM {self.schema}.{self.table} WHERE id = $1", params=[project_id])
        return True

    async def set_instructions(self, project_id: str, instructions: str) -> bool:
        return bool(await self.update_project(project_id, custom_instructions=instructions))

    async def count_projects(self, user_id: str) -> int:
        async with self.db:
            rows = await self.db.fetch(f"SELECT COUNT(*) as cnt FROM {self.schema}.{self.table} WHERE user_id = $1", params=[user_id])
        return rows[0]["cnt"] if rows else 0
