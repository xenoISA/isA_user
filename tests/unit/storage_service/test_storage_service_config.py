"""L1 Unit — Storage service configuration defaults."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from microservices.storage_service.storage_service import StorageService


def _make_config(bucket_name):
    return SimpleNamespace(minio_bucket_name=bucket_name)


def _make_config_manager():
    manager = MagicMock()
    manager.discover_service.return_value = ("localhost", 9000)
    return manager


@patch("microservices.storage_service.storage_service.AsyncMinIOClient")
@patch("microservices.storage_service.storage_service.StorageOrganizationClient")
@patch("microservices.storage_service.storage_service.StorageRepository")
def test_storage_service_defaults_bucket_name_when_config_value_is_none(
    _repo_cls,
    _org_client_cls,
    _minio_client_cls,
):
    service = StorageService(
        config=_make_config(None),
        config_manager=_make_config_manager(),
    )

    assert service.bucket_name == "isa-storage"


@patch("microservices.storage_service.storage_service.AsyncMinIOClient")
@patch("microservices.storage_service.storage_service.StorageOrganizationClient")
@patch("microservices.storage_service.storage_service.StorageRepository")
def test_storage_service_respects_explicit_bucket_name(
    _repo_cls,
    _org_client_cls,
    _minio_client_cls,
):
    service = StorageService(
        config=_make_config("custom-bucket"),
        config_manager=_make_config_manager(),
    )

    assert service.bucket_name == "custom-bucket"
