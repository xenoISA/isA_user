"""Alembic environment configuration for isA_user platform.

Supports per-service migrations via: alembic -x service=<name>
Each service gets its own version table and version directory.
"""

import sys
from pathlib import Path

from alembic import context
from alembic.script import ScriptDirectory
from sqlalchemy import engine_from_config, pool

# Add project root to path so we can import core.migration_helpers
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.migration_helpers import (
    get_database_url,
    get_service_version_path,
    get_version_table,
    validate_service_name,
)

config = context.config

# Read the service name from -x service=<name>
service_name = context.get_x_argument(as_dictionary=True).get("service", "")
validate_service_name(service_name)

# Override sqlalchemy.url from environment variables
config.set_main_option("sqlalchemy.url", get_database_url())

# Set per-service version locations and version table.
#
# Alembic's `ScriptDirectory` is constructed from `config` BEFORE env.py
# runs, so updating `version_locations` here would not affect the bound
# script — the CLI would still resolve revisions from the default
# `alembic/versions/` (which is empty). We rebuild the ScriptDirectory
# and reassign it on the environment context so per-service revisions
# are actually discovered.
version_path = str(get_service_version_path(service_name))
config.set_main_option("version_locations", version_path)
version_table = get_version_table(service_name)

# Rebuild ScriptDirectory with the per-service version path. Mutate the
# existing script in place because the alembic CLI's CommandLine has
# already captured the original ScriptDirectory reference — reassigning
# `context.script` does not propagate.
_rebuilt = ScriptDirectory.from_config(config)
_script = context.script
_script.dir = _rebuilt.dir
_script._version_locations = _rebuilt._version_locations
_script.revision_map = _rebuilt.revision_map


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL without DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=version_table,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
            version_table=version_table,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
