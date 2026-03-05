"""Alembic migration helpers.

Shared logic for building database URLs, resolving service paths,
and validating service names. Used by env.py and testable independently.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_database_url() -> str:
    """Build PostgreSQL connection URL from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    db = os.getenv("POSTGRES_DB", "isa_platform")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_service_version_path(service_name: str) -> Path:
    """Return the alembic versions directory for a given service."""
    return PROJECT_ROOT / "microservices" / service_name / "alembic" / "versions"


def get_version_table(service_name: str) -> str:
    """Return the alembic_version table name for a service.

    Each service tracks its own migration state independently.
    """
    return f"alembic_version_{service_name}"


def list_migratable_services() -> list[str]:
    """List all services that have an alembic/versions directory."""
    microservices_dir = PROJECT_ROOT / "microservices"
    services = []
    if microservices_dir.is_dir():
        for service_dir in sorted(microservices_dir.iterdir()):
            versions_dir = service_dir / "alembic" / "versions"
            if versions_dir.is_dir():
                services.append(service_dir.name)
    return services


def validate_service_name(service_name: str) -> None:
    """Validate that a service name has an alembic/versions directory.

    Raises ValueError if the service doesn't exist or has no migrations.
    """
    if not service_name:
        raise ValueError("Service name is required. Use: alembic -x service=<name>")

    versions_path = get_service_version_path(service_name)
    if not versions_path.is_dir():
        available = list_migratable_services()
        msg = f"Service '{service_name}' has no alembic/versions directory."
        if available:
            msg += f" Available: {', '.join(available)}"
        raise ValueError(msg)
