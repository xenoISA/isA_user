"""L1 Unit tests for core.migration_helpers module."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from core.migration_helpers import (
    get_database_url,
    get_service_version_path,
    get_version_table,
    list_migratable_services,
    validate_service_name,
    PROJECT_ROOT,
)


class TestGetDatabaseUrl:
    def test_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            url = get_database_url()
        assert url == "postgresql://postgres:@localhost:5432/isa_platform"

    def test_from_env(self):
        env = {
            "POSTGRES_HOST": "db.example.com",
            "POSTGRES_PORT": "5433",
            "POSTGRES_USER": "admin",
            "POSTGRES_PASSWORD": "secret",
            "POSTGRES_DB": "mydb",
        }
        with patch.dict(os.environ, env, clear=True):
            url = get_database_url()
        assert url == "postgresql://admin:secret@db.example.com:5433/mydb"

    def test_partial_env(self):
        env = {"POSTGRES_HOST": "remote", "POSTGRES_PASSWORD": "pass"}
        with patch.dict(os.environ, env, clear=True):
            url = get_database_url()
        assert url == "postgresql://postgres:pass@remote:5432/isa_platform"


class TestGetServiceVersionPath:
    def test_returns_correct_path(self):
        path = get_service_version_path("account_service")
        expected = PROJECT_ROOT / "microservices" / "account_service" / "alembic" / "versions"
        assert path == expected

    def test_different_service(self):
        path = get_service_version_path("auth_service")
        assert path.name == "versions"
        assert "auth_service" in str(path)


class TestGetVersionTable:
    def test_naming(self):
        assert get_version_table("account_service") == "alembic_version_account_service"
        assert get_version_table("auth_service") == "alembic_version_auth_service"
        assert get_version_table("payment_service") == "alembic_version_payment_service"


class TestListMigratableServices:
    def test_finds_services_with_alembic_dirs(self, tmp_path, monkeypatch):
        """Services with alembic/versions/ are listed; others are not."""
        monkeypatch.setattr("core.migration_helpers.PROJECT_ROOT", tmp_path)

        ms = tmp_path / "microservices"
        # Service with alembic dir
        (ms / "svc_a" / "alembic" / "versions").mkdir(parents=True)
        # Service without alembic dir (has old-style migrations/)
        (ms / "svc_b" / "migrations").mkdir(parents=True)
        # Another service with alembic
        (ms / "svc_c" / "alembic" / "versions").mkdir(parents=True)

        result = list_migratable_services()
        assert result == ["svc_a", "svc_c"]

    def test_empty_when_no_microservices(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.migration_helpers.PROJECT_ROOT", tmp_path)
        assert list_migratable_services() == []


class TestValidateServiceName:
    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="Service name is required"):
            validate_service_name("")

    def test_nonexistent_service_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.migration_helpers.PROJECT_ROOT", tmp_path)
        (tmp_path / "microservices").mkdir()

        with pytest.raises(ValueError, match="no alembic/versions directory"):
            validate_service_name("nonexistent_service")

    def test_valid_service_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.migration_helpers.PROJECT_ROOT", tmp_path)
        (tmp_path / "microservices" / "account_service" / "alembic" / "versions").mkdir(parents=True)

        # Should not raise
        validate_service_name("account_service")

    def test_error_lists_available_services(self, tmp_path, monkeypatch):
        monkeypatch.setattr("core.migration_helpers.PROJECT_ROOT", tmp_path)
        (tmp_path / "microservices" / "auth_service" / "alembic" / "versions").mkdir(parents=True)

        with pytest.raises(ValueError, match="Available: auth_service"):
            validate_service_name("bad_service")
