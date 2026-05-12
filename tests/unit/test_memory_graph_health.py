"""Health probe naming for the Falkor-backed memory graph."""

from unittest.mock import AsyncMock

import pytest

from core.health import HealthCheck


@pytest.mark.anyio
async def test_memory_graph_health_uses_memory_graph_dependency_name():
    graph_client = AsyncMock()
    graph_client.health_check = AsyncMock(return_value=True)
    health = HealthCheck("memory_service")

    health.add_memory_graph(lambda: graph_client)

    response = await health.check()
    data = response.body.decode()

    assert response.status_code == 200
    assert '"memory_graph":{"status":"healthy"}' in data
    assert '"neo4j"' not in data


@pytest.mark.anyio
async def test_add_neo4j_remains_available_for_existing_services():
    graph_client = AsyncMock()
    graph_client.health_check = AsyncMock(return_value=True)
    health = HealthCheck("legacy_graph_service")

    health.add_neo4j(lambda: graph_client)

    response = await health.check()
    data = response.body.decode()

    assert response.status_code == 200
    assert '"neo4j":{"status":"healthy"}' in data
