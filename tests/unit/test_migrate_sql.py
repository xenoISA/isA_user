import importlib.util
from pathlib import Path
import sys

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "migrate_sql.py"
)

spec = importlib.util.spec_from_file_location("migrate_sql", SCRIPT_PATH)
migrate_sql = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = migrate_sql
spec.loader.exec_module(migrate_sql)


@pytest.mark.unit
def test_managed_sql_migration_filter(tmp_path: Path):
    managed = tmp_path / "001_create_table.sql"
    managed.write_text("-- migration\n")
    deprecated = tmp_path / "002_old.sql.deprecated"
    deprecated.write_text("-- deprecated\n")
    test_data = tmp_path / "999_insert_test_data.sql"
    test_data.write_text("-- test data\n")

    assert migrate_sql._is_managed_sql_migration(managed) is True
    assert migrate_sql._is_managed_sql_migration(deprecated) is False
    assert migrate_sql._is_managed_sql_migration(test_data) is False


@pytest.mark.unit
def test_get_service_migrations_returns_sorted_checksums(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    project_root = tmp_path
    service_dir = project_root / "microservices" / "billing_service" / "migrations"
    service_dir.mkdir(parents=True)
    second = service_dir / "002_second.sql"
    first = service_dir / "001_first.sql"
    second.write_text("-- second\n")
    first.write_text("-- first\n")

    monkeypatch.setattr(migrate_sql, "MICROSERVICES_ROOT", project_root / "microservices")

    migrations = migrate_sql.get_service_migrations("billing_service")

    assert [migration.migration_name for migration in migrations] == [
        "001_first.sql",
        "002_second.sql",
    ]
    assert all(len(migration.checksum) == 64 for migration in migrations)


@pytest.mark.unit
def test_baseline_service_migrations_marks_up_to_through_version(monkeypatch: pytest.MonkeyPatch):
    migrations = [
        migrate_sql.SqlMigration(
            service_name="billing_service",
            path=Path("/tmp/001_first.sql"),
            version=1,
            checksum="a" * 64,
        ),
        migrate_sql.SqlMigration(
            service_name="billing_service",
            path=Path("/tmp/002_second.sql"),
            version=2,
            checksum="b" * 64,
        ),
        migrate_sql.SqlMigration(
            service_name="billing_service",
            path=Path("/tmp/006_third.sql"),
            version=6,
            checksum="c" * 64,
        ),
    ]
    recorded: list[str] = []

    monkeypatch.setattr(migrate_sql, "get_service_migrations", lambda service_name: migrations)
    monkeypatch.setattr(migrate_sql, "get_applied_migrations", lambda database_url, service_name: {})
    monkeypatch.setattr(
        migrate_sql,
        "record_applied_migration",
        lambda database_url, migration: recorded.append(migration.migration_name),
    )

    migrate_sql.baseline_service_migrations(
        "postgresql://example",
        "billing_service",
        through_version=2,
    )

    assert recorded == ["001_first.sql", "002_second.sql"]


@pytest.mark.unit
def test_baseline_service_migrations_detects_checksum_drift(monkeypatch: pytest.MonkeyPatch):
    migrations = [
        migrate_sql.SqlMigration(
            service_name="billing_service",
            path=Path("/tmp/001_first.sql"),
            version=1,
            checksum="a" * 64,
        ),
    ]

    monkeypatch.setattr(migrate_sql, "get_service_migrations", lambda service_name: migrations)
    monkeypatch.setattr(
        migrate_sql,
        "get_applied_migrations",
        lambda database_url, service_name: {"001_first.sql": "b" * 64},
    )

    with pytest.raises(RuntimeError, match="Checksum drift detected"):
        migrate_sql.baseline_service_migrations("postgresql://example", "billing_service")
