"""Consul registration helpers for platform gateway discovery."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .routes_registry import SERVICE_METADATA, get_routes_for_consul
from .config import Settings

logger = logging.getLogger(__name__)


def build_service_meta(settings: Settings) -> dict[str, str]:
    """Build APISIX sync metadata using the isA Consul route convention."""
    auth_required = "true" if settings.consul_auth_required else "false"
    return {
        "api_path": settings.base_path,
        "base_path": settings.base_path,
        "auth_required": auth_required,
        "rate_limit": str(settings.consul_rate_limit),
        **get_routes_for_consul(),
    }


@dataclass
class ServiceRegistration:
    settings: Settings
    registry: Any | None = None

    @property
    def service_id(self) -> str:
        return (
            f"{self.settings.service_name}-"
            f"{self.settings.service_host}-"
            f"{self.settings.service_port}"
        )

    def register(self) -> None:
        """Register this service with Consul for APISIX route sync."""
        try:
            from isa_common.consul_client import ConsulRegistry
        except ImportError as exc:
            raise RuntimeError(
                "CONSUL_ENABLED=true requires isa_common.consul_client to be importable."
            ) from exc

        self.registry = ConsulRegistry(
            service_name=SERVICE_METADATA["service_name"],
            service_port=self.settings.service_port,
            consul_host=self.settings.consul_host,
            consul_port=self.settings.consul_port,
            tags=list(self.settings.consul_tags),
            meta=build_service_meta(self.settings),
            health_check_type="ttl",
        )
        self.registry.register()
        self.registry.start_maintenance()
        logger.info(
            "Registered %s with Consul at %s:%s for %s",
            self.settings.service_name,
            self.settings.service_host,
            self.settings.service_port,
            self.settings.base_path,
        )

    def deregister(self) -> None:
        """Remove this service registration on graceful shutdown."""
        if self.registry is not None:
            self.registry.deregister()
        logger.info("Deregistered %s from Consul", self.service_id)


def create_service_registration(settings: Settings) -> ServiceRegistration | None:
    """Create a registration when discovery is enabled."""
    if not settings.consul_enabled:
        return None

    return ServiceRegistration(settings=settings)
