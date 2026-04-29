"""L1 Unit — Storage service client internal-auth forwarding."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from microservices.storage_service.client import StorageServiceClient
from core.auth_dependencies import INTERNAL_SERVICE_SECRET


def _make_response(payload=None):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload if payload is not None else {}
    return response


@pytest.mark.asyncio
async def test_upload_file_uses_internal_service_headers():
    client = StorageServiceClient(base_url="http://storage.local")
    client.client.post = AsyncMock(
        return_value=_make_response(
            {"file_id": "file-1", "file_path": "storage/file-1"}
        )
    )

    await client.upload_file(
        file_content=b"hello",
        filename="guide.md",
        user_id="user-1",
        metadata={"project_id": "project-1"},
    )

    kwargs = client.client.post.await_args.kwargs
    assert kwargs["headers"] == {
        "X-Internal-Service": "true",
        "X-Internal-Service-Secret": INTERNAL_SERVICE_SECRET,
    }

    await client.close()


@pytest.mark.asyncio
async def test_delete_file_uses_internal_service_headers():
    client = StorageServiceClient(base_url="http://storage.local")
    client.client.delete = AsyncMock(return_value=_make_response())

    deleted = await client.delete_file("file-1", "user-1", permanent=True)

    assert deleted is True
    kwargs = client.client.delete.await_args.kwargs
    assert kwargs["headers"] == {
        "X-Internal-Service": "true",
        "X-Internal-Service-Secret": INTERNAL_SERVICE_SECRET,
    }
    assert kwargs["params"] == {"user_id": "user-1", "permanent": True}

    await client.close()


def test_storage_service_url_env_override(monkeypatch):
    monkeypatch.setenv("STORAGE_SERVICE_URL", "http://127.0.0.1:8209/")

    client = StorageServiceClient()

    assert client.base_url == "http://127.0.0.1:8209"

    import asyncio

    asyncio.run(client.close())
