"""Project Service Factory (#258, #295, #298)"""
import logging
from typing import Optional

from core.config_manager import ConfigManager

from .protocols import ProjectRepositoryProtocol, EventBusProtocol
from .project_repository import ProjectRepository
from .project_service import ProjectService

logger = logging.getLogger(__name__)


def create_project_service(
    config_manager: ConfigManager,
    repository: Optional[ProjectRepositoryProtocol] = None,
    event_bus: Optional[EventBusProtocol] = None,
) -> ProjectService:
    repo = repository or ProjectRepository(config_manager=config_manager)
    return ProjectService(repository=repo, event_bus=event_bus)
