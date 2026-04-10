#!/usr/bin/env python3
"""Tracked raw SQL migration runner for microservice migration directories."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.migration_helpers import get_database_url

MICROSERVICES_ROOT = PROJECT_ROOT / "microservices"
HISTORY_TABLE = "public.service_sql_migrations"
MIGRATION_PATTERN = re.compile(r"^(?P<version>\d{3})_[a-z0-9_]+\.sql$")


@dataclass(frozen=True)
class SqlMigration:
    service_name: str
    path: Path
    version: int
    checksum: str

    @property
    def migration_name(self) -> str:
        return self.path.name


def _run_psql(
    database_url: str,
    *args: str,
    input_sql: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["psql", database_url, *args],
        input=input_sql,
        text=True,
        capture_output=True,
        check=True,
    )


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _is_managed_sql_migration(path: Path) -> bool:
    name = path.name
    if not path.is_file() or path.suffix != ".sql":
        return False
    if name.endswith(".deprecated") or name.startswith("999_"):
        return False
    if "test_data" in name or name.startswith("cleanup"):
        return False
    return MIGRATION_PATTERN.match(name) is not None


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_sql_migratable_services() -> list[str]:
    services: list[str] = []
    for service_dir in sorted(MICROSERVICES_ROOT.iterdir()):
        migrations_dir = service_dir / "migrations"
        if not migrations_dir.is_dir():
            continue
        if any(_is_managed_sql_migration(path) for path in migrations_dir.iterdir()):
            services.append(service_dir.name)
    return services


def get_service_migrations(service_name: str) -> list[SqlMigration]:
    migrations_dir = MICROSERVICES_ROOT / service_name / "migrations"
    if not migrations_dir.is_dir():
        raise ValueError(f"Service '{service_name}' has no migrations directory")

    migrations: list[SqlMigration] = []
    for path in sorted(migrations_dir.iterdir()):
        if not _is_managed_sql_migration(path):
            continue
        match = MIGRATION_PATTERN.match(path.name)
        if not match:
            continue
        migrations.append(
            SqlMigration(
                service_name=service_name,
                path=path,
                version=int(match.group("version")),
                checksum=_checksum(path),
            )
        )
    return migrations


def iter_target_services(service_name: str) -> Iterable[str]:
    if service_name == "all":
        return list_sql_migratable_services()
    return [service_name]


def ensure_history_table(database_url: str) -> None:
    sql = f"""
    CREATE TABLE IF NOT EXISTS {HISTORY_TABLE} (
        id BIGSERIAL PRIMARY KEY,
        service_name VARCHAR(100) NOT NULL,
        migration_name VARCHAR(255) NOT NULL,
        version INTEGER NOT NULL,
        checksum VARCHAR(64) NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (service_name, migration_name)
    );
    """
    _run_psql(database_url, "-v", "ON_ERROR_STOP=1", "-c", sql)


def get_applied_migrations(database_url: str, service_name: str) -> dict[str, str]:
    query = (
        f"SELECT migration_name, checksum FROM {HISTORY_TABLE} "
        f"WHERE service_name = '{_sql_literal(service_name)}' ORDER BY version;"
    )
    result = _run_psql(database_url, "-At", "-F", "\t", "-c", query)
    applied: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        migration_name, checksum = line.split("\t", 1)
        applied[migration_name] = checksum
    return applied


def record_applied_migration(database_url: str, migration: SqlMigration) -> None:
    query = (
        f"INSERT INTO {HISTORY_TABLE} "
        f"(service_name, migration_name, version, checksum) VALUES "
        f"('{_sql_literal(migration.service_name)}', "
        f"'{_sql_literal(migration.migration_name)}', "
        f"{migration.version}, "
        f"'{migration.checksum}') "
        f"ON CONFLICT (service_name, migration_name) DO NOTHING;"
    )
    _run_psql(database_url, "-v", "ON_ERROR_STOP=1", "-c", query)


def baseline_service_migrations(
    database_url: str,
    service_name: str,
    through_version: int | None = None,
) -> None:
    migrations = get_service_migrations(service_name)
    applied = get_applied_migrations(database_url, service_name)

    if not migrations:
        print(f"[baseline] {service_name}: no managed SQL migrations")
        return

    for migration in migrations:
        if through_version is not None and migration.version > through_version:
            continue

        applied_checksum = applied.get(migration.migration_name)
        if applied_checksum:
            if applied_checksum != migration.checksum:
                raise RuntimeError(
                    f"Checksum drift detected for {service_name}/{migration.migration_name}"
                )
            print(f"[skip] {service_name}: {migration.migration_name}")
            continue

        print(f"[baseline] {service_name}: {migration.migration_name}")
        record_applied_migration(database_url, migration)


def apply_service_migrations(database_url: str, service_name: str) -> None:
    migrations = get_service_migrations(service_name)
    applied = get_applied_migrations(database_url, service_name)

    if not migrations:
        print(f"[sql-upgrade] {service_name}: no managed SQL migrations")
        return

    for migration in migrations:
        applied_checksum = applied.get(migration.migration_name)
        if applied_checksum:
            if applied_checksum != migration.checksum:
                raise RuntimeError(
                    f"Checksum drift detected for {service_name}/{migration.migration_name}"
                )
            print(f"[skip] {service_name}: {migration.migration_name}")
            continue

        print(f"[apply] {service_name}: {migration.migration_name}")
        _run_psql(
            database_url,
            "-v",
            "ON_ERROR_STOP=1",
            "-1",
            "-f",
            str(migration.path),
        )
        record_applied_migration(database_url, migration)


def show_status(database_url: str, service_name: str) -> None:
    migrations = get_service_migrations(service_name)
    applied = get_applied_migrations(database_url, service_name)

    if not migrations:
        print(f"{service_name}: no managed SQL migrations")
        return

    print(f"{service_name}:")
    for migration in migrations:
        status = "applied" if migration.migration_name in applied else "pending"
        print(f"  [{status}] {migration.migration_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["list", "status", "upgrade", "baseline"])
    parser.add_argument(
        "service",
        nargs="?",
        default="all",
        help="Service name or 'all' (default: all)",
    )
    parser.add_argument(
        "--through-version",
        type=int,
        default=None,
        help="For baseline only: mark migrations up to and including this version as already applied",
    )
    args = parser.parse_args()

    database_url = get_database_url()

    if args.command == "list":
        for service_name in list_sql_migratable_services():
            print(service_name)
        return 0

    ensure_history_table(database_url)

    try:
        if args.command == "upgrade":
            for service_name in iter_target_services(args.service):
                apply_service_migrations(database_url, service_name)
            return 0

        if args.command == "baseline":
            for service_name in iter_target_services(args.service):
                baseline_service_migrations(
                    database_url,
                    service_name,
                    through_version=args.through_version,
                )
            return 0

        if args.command == "status":
            for service_name in iter_target_services(args.service):
                show_status(database_url, service_name)
            return 0
    except (RuntimeError, subprocess.CalledProcessError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
