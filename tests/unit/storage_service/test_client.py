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


@pytest.mark.asyncio
async def test_export_user_data_collects_storage_inventory_and_metadata():
    client = StorageServiceClient(base_url="http://storage.local")
    client.list_files = AsyncMock(
        return_value=[
            {"file_id": "file-1", "filename": "guide.md"},
            {"file_id": "file-2", "filename": "photo.jpg"},
        ]
    )
    client.get_storage_stats = AsyncMock(return_value={"total_files": 2})
    client.get_storage_quota = AsyncMock(return_value={"used_bytes": 2048})
    client.list_user_albums = AsyncMock(
        return_value={"albums": [{"album_id": "album-1", "name": "Launch"}]}
    )
    client.get_intelligence_stats = AsyncMock(return_value={"indexed_files": 2})

    result = await client.export_user_data(
        user_id="user-1",
        organization_id="org-1",
        request_id="gdpr_req_1",
    )

    assert result["schema_version"] == "storage-export-v1"
    assert result["service"] == "storage_service"
    assert result["user_id"] == "user-1"
    assert result["organization_id"] == "org-1"
    assert result["gdpr_request_id"] == "gdpr_req_1"
    assert [item["file_id"] for item in result["files"]] == ["file-1", "file-2"]
    assert result["albums"]["albums"][0]["album_id"] == "album-1"
    assert result["storage_stats"] == {"total_files": 2}
    assert result["storage_quota"] == {"used_bytes": 2048}
    assert result["intelligence_stats"] == {"indexed_files": 2}
    assert result["counts"] == {
        "records": 3,
        "sections": {
            "files": 2,
            "albums": 1,
            "storage_stats": 1,
            "storage_quota": 1,
            "intelligence_stats": 1,
        },
    }
    client.list_files.assert_awaited_once_with(
        user_id="user-1",
        organization_id="org-1",
        limit=1000,
        offset=0,
    )
    client.list_user_albums.assert_awaited_once_with(
        user_id="user-1",
        limit=1000,
        offset=0,
    )
    await client.close()


@pytest.mark.asyncio
async def test_storage_service_url_env_override(monkeypatch):
    monkeypatch.setenv("STORAGE_SERVICE_URL", "http://127.0.0.1:8209/")

    client = StorageServiceClient()

    assert client.base_url == "http://127.0.0.1:8209"
    await client.close()
