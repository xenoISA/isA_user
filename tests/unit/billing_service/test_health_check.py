from __future__ import annotations

from types import SimpleNamespace

import pytest

from microservices.billing_service import main as billing_main


class AsyncHealthyDB:
    async def health_check(self):
        return True


class AsyncUnhealthyDB:
    async def health_check(self):
        return False


@pytest.mark.asyncio
async def test_health_check_awaits_async_database_health():
    original_repository = billing_main.repository
    billing_main.repository = SimpleNamespace(db=AsyncHealthyDB())
    try:
        response = await billing_main.health_check()
    finally:
        billing_main.repository = original_repository

    assert response.status == "healthy"
    assert response.dependencies["database"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_reports_unhealthy_when_async_database_fails():
    original_repository = billing_main.repository
    billing_main.repository = SimpleNamespace(db=AsyncUnhealthyDB())
    try:
        response = await billing_main.health_check()
    finally:
        billing_main.repository = original_repository

    assert response.status == "degraded"
    assert response.dependencies["database"] == "unhealthy"
