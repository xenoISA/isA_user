"""Project Service Factory (#258, #295, #298)"""
import logging
from typing import Optional

from core.config_manager import ConfigManager

from microservices.storage_service.client import StorageServiceClient

from .protocols import ProjectRepositoryProtocol, EventBusProtocol, StorageServiceProtocol
from .project_repository import ProjectRepository
from .project_service import ProjectService

logger = logging.getLogger(__name__)


def create_project_service(
    config_manager: ConfigManager,
    repository: Optional[ProjectRepositoryProtocol] = None,
    storage_client: Optional[StorageServiceProtocol] = None,
    event_bus: Optional[EventBusProtocol] = None,
) -> ProjectService:
    repo = repository or ProjectRepository(config_manager=config_manager)
    storage = storage_client or StorageServiceClient()
    return ProjectService(repository=repo, storage_client=storage, event_bus=event_bus)
