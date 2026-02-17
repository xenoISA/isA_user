"""
PostgreSQL Client Wrapper for isA Cloud Platform

Centralized PostgreSQL client wrapper using AsyncPostgresClient from isa_common.
Provides service discovery integration and consistent database access pattern.

Usage:
    from core.postgres_client import get_postgres_client

    # Get client instance
    db = await get_postgres_client("album_service")

    # Execute queries
    async with db:
        result = await db.query("SELECT * FROM albums WHERE user_id = $1", [user_id])
"""

import logging
import os
from typing import Any, Dict, List, Optional

from isa_common import AsyncPostgresClient

logger = logging.getLogger(__name__)


class PostgresClientWrapper:
    """
    PostgreSQL client wrapper with service discovery integration.

    Wraps AsyncPostgresClient from isa_common and provides:
    - Service discovery for host/port configuration
    - Consistent initialization pattern
    - Environment variable fallbacks
    """

    def __init__(
        self,
        service_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ):
        """
        Initialize PostgreSQL client wrapper.

        Args:
            service_name: Name of the service using this client
            host: PostgreSQL host (defaults to env/service discovery)
            port: PostgreSQL port (defaults to 5432)
            database: Database name (defaults to 'postgres')
            username: Database username
            password: Database password
            user_id: User ID for multi-tenant operations
            organization_id: Organization ID for multi-tenant operations
        """
        from core.config_manager import ConfigManager

        self.service_name = service_name

        # Use ConfigManager for service discovery
        config = ConfigManager(service_name)
        discovered_host, discovered_port = config.discover_service(
            service_name="postgres_service",
            default_host="postgres",
            default_port=5432,
            env_host_key="POSTGRES_HOST",
            env_port_key="POSTGRES_PORT",
        )

        # Apply overrides
        self.host = host or discovered_host
        self.port = port or discovered_port
        self.database = database or os.getenv("POSTGRES_DB", "postgres")
        self.username = username or os.getenv("POSTGRES_USER", "postgres")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "")
        self.user_id = user_id or service_name
        self.organization_id = organization_id or os.getenv("ORGANIZATION_ID", "default-org")

        # Create underlying client
        self._client = AsyncPostgresClient(
            host=self.host,
            port=self.port,
            database=self.database,
            username=self.username,
            password=self.password,
            user_id=self.user_id,
            organization_id=self.organization_id,
        )

        logger.info(f"PostgreSQL client initialized for {service_name}: {self.host}:{self.port}/{self.database}")

    @property
    def client(self) -> AsyncPostgresClient:
        """Get underlying AsyncPostgresClient"""
        return self._client

    async def __aenter__(self):
        """Async context manager entry"""
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._client.__aexit__(exc_type, exc_val, exc_tb)

    async def health_check(self) -> Optional[Dict]:
        """Check database health"""
        return await self._client.health_check()

    async def query(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        return await self._client.query(sql, params)

    async def query_row(self, sql: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
        """Execute query and return single row"""
        return await self._client.query_row(sql, params)

    async def execute(self, sql: str, params: Optional[List[Any]] = None) -> bool:
        """Execute SQL statement"""
        return await self._client.execute(sql, params)

    async def execute_many(self, sql: str, params_list: List[List[Any]]) -> bool:
        """Execute SQL statement with multiple parameter sets"""
        return await self._client.execute_many(sql, params_list)

    async def close(self):
        """Close connection"""
        await self._client.close()


# Singleton instances per service
_postgres_clients: Dict[str, PostgresClientWrapper] = {}


async def get_postgres_client(
    service_name: str,
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    **kwargs,
) -> PostgresClientWrapper:
    """
    Get or create PostgreSQL client for a service.

    Args:
        service_name: Service name
        host: Optional host override
        port: Optional port override
        database: Optional database override
        **kwargs: Additional client options

    Returns:
        PostgresClientWrapper instance
    """
    global _postgres_clients

    if service_name not in _postgres_clients:
        client = PostgresClientWrapper(
            service_name=service_name,
            host=host,
            port=port,
            database=database,
            **kwargs,
        )
        _postgres_clients[service_name] = client

    return _postgres_clients[service_name]
