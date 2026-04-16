"""Project Service Factory (#258)"""
from typing import Optional
from core.config_manager import ConfigManager
from .project_service import ProjectService

def create_project_service(config_manager: Optional[ConfigManager] = None) -> ProjectService:
    return ProjectService(config_manager=config_manager)
