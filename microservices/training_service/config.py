"""Environment-backed settings for the training microservice."""

from __future__ import annotations

import os
from dataclasses import dataclass

from . import __version__


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    service_name: str
    service_port: int
    environment: str
    version: str
    base_path: str = "/api/v1/training"
    service_host: str = "user-training-service"
    consul_enabled: bool = False
    consul_host: str = "localhost"
    consul_port: int = 8500
    consul_auth_required: bool = False
    consul_rate_limit: int = 100
    consul_tags: tuple[str, ...] = ("isa", "training", "api")
    auth_mode: str = "development"
    auth_service_url: str = "http://localhost:8201"
    training_persistence_backend: str = "memory"
    training_database_url: str | None = None
    training_state_path: str | None = None
    sandbox_execution_enabled: bool = True


def get_settings() -> Settings:
    """Load settings from environment variables."""
    environment = (
        os.getenv("ENVIRONMENT")
        or os.getenv("ISA_ENV")
        or os.getenv("ENV")
        or "development"
    )
    training_state_path = os.getenv("TRAINING_STATE_PATH") or None
    persistence_backend = (
        os.getenv(
            "TRAINING_PERSISTENCE_BACKEND",
            "json" if training_state_path else "memory",
        )
        .strip()
        .lower()
    )

    return Settings(
        service_name=os.getenv("SERVICE_NAME", "training_service"),
        service_port=_int_env("SERVICE_PORT", 8262),
        environment=environment,
        version=os.getenv("SERVICE_VERSION", __version__),
        base_path=os.getenv("API_BASE_PATH", "/api/v1/training"),
        service_host=os.getenv("SERVICE_HOST", "user-training-service"),
        consul_enabled=_bool_env("CONSUL_ENABLED", False),
        consul_host=os.getenv("CONSUL_HOST", "localhost"),
        consul_port=_int_env("CONSUL_PORT", 8500),
        consul_auth_required=_bool_env("CONSUL_AUTH_REQUIRED", False),
        consul_rate_limit=_int_env("CONSUL_RATE_LIMIT", 100),
        consul_tags=_csv_env("CONSUL_TAGS", ("isa", "training", "api")),
        auth_mode=os.getenv("TRAINING_AUTH_MODE", "development"),
        auth_service_url=os.getenv("AUTH_SERVICE_URL", "http://localhost:8201"),
        training_persistence_backend=persistence_backend,
        training_database_url=(
            os.getenv("TRAINING_DATABASE_URL") or os.getenv("DATABASE_URL") or None
        ),
        training_state_path=training_state_path,
        sandbox_execution_enabled=_bool_env("TRAINING_SANDBOX_EXECUTION_ENABLED", True),
    )
