"""Project Service Factory (#258, #295, #298, #442)"""

import logging
from typing import Any, Optional

from core.config_manager import ConfigManager

from microservices.storage_service.client import StorageServiceClient

from .clients import ProjectSharingClient
from .protocols import (
    ProjectRepositoryProtocol,
    EventBusProtocol,
    OrganizationAccessProtocol,
    StorageServiceProtocol,
)
from .project_repository import ProjectRepository
from .project_service import ProjectService

logger = logging.getLogger(__name__)


def create_project_service(
    config_manager: ConfigManager,
    repository: Optional[ProjectRepositoryProtocol] = None,
    storage_client: Optional[StorageServiceProtocol] = None,
    event_bus: Optional[EventBusProtocol] = None,
    organization_access: Optional[OrganizationAccessProtocol] = None,
    project_sharing_client: Optional[Any] = None,
) -> ProjectService:
    repo = repository or ProjectRepository(config_manager=config_manager)
    storage = storage_client or StorageServiceClient()
    if organization_access is None:
        from microservices.organization_service.client import OrganizationServiceClient

        organization_access = OrganizationServiceClient()
    sharing_client = project_sharing_client or ProjectSharingClient()
    return ProjectService(
        repository=repo,
        storage_client=storage,
        event_bus=event_bus,
        organization_access=organization_access,
        project_sharing_client=sharing_client,
    )
