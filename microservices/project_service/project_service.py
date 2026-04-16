"""Project Service — Business logic (#258)"""
import logging
from typing import Optional, List, Dict, Any

from .project_repository import ProjectRepository, ProjectNotFoundError

logger = logging.getLogger(__name__)

class ProjectService:
    def __init__(self, repository: ProjectRepository = None, config_manager=None):
        self.repository = repository or ProjectRepository(config_manager=config_manager)

    async def create_project(self, user_id: str, name: str, description: str = None, custom_instructions: str = None) -> Dict[str, Any]:
        return await self.repository.create_project(user_id, name, description, custom_instructions)

    async def get_project(self, project_id: str, user_id: str) -> Dict[str, Any]:
        project = await self.repository.get_project(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        if project["user_id"] != user_id:
            raise PermissionError("Not authorized to access this project")
        return project

    async def list_projects(self, user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        return await self.repository.list_projects(user_id, limit, offset)

    async def update_project(self, project_id: str, user_id: str, **updates) -> Dict[str, Any]:
        await self.get_project(project_id, user_id)  # ownership check
        return await self.repository.update_project(project_id, **updates)

    async def delete_project(self, project_id: str, user_id: str) -> bool:
        await self.get_project(project_id, user_id)  # ownership check
        return await self.repository.delete_project(project_id)

    async def set_instructions(self, project_id: str, user_id: str, instructions: str) -> bool:
        await self.get_project(project_id, user_id)  # ownership check
        return await self.repository.set_instructions(project_id, instructions)
