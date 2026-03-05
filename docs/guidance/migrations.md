# Database Migrations Guide

This project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema versioning with raw SQL execution (no ORM).

## Architecture

- **Single database** (`isa_platform`) with **per-service schemas** (e.g., `account`, `auth`, `payment`)
- **Per-service migration histories** — each service tracks its own `alembic_version_<service>` table
- **Shared configuration** — one `alembic.ini` at project root, one `alembic/env.py`
- **Service selection** via `-x service=<name>` flag

```
alembic.ini                                    # Shared config
alembic/
  env.py                                       # Reads -x service=<name>, routes to correct versions dir
  script.py.mako                               # Template for new revisions
microservices/
  account_service/alembic/versions/            # Account service migrations
  auth_service/alembic/versions/               # Auth service migrations
  payment_service/alembic/versions/            # Payment service migrations
```

## Quick Start

```bash
# Install dependencies (if not already)
pip install alembic sqlalchemy

# Upgrade a single service
alembic -x service=account_service upgrade head

# Upgrade all services
./scripts/migrate.sh upgrade all

# Check migration status
./scripts/migrate.sh status all

# Rollback one step
alembic -x service=payment_service downgrade -1
```

## Creating a New Migration

```bash
# Using the helper script
./scripts/migrate.sh revision account_service -m "add phone number column"

# Or directly with alembic
alembic -x service=account_service revision -m "add phone number column"
```

This creates a new file in `microservices/account_service/alembic/versions/`.

Edit the generated file to add your SQL:

```python
def upgrade() -> None:
    op.execute("ALTER TABLE account.users ADD COLUMN phone VARCHAR(20)")

def downgrade() -> None:
    op.execute("ALTER TABLE account.users DROP COLUMN IF EXISTS phone")
```

## Rules

1. Every `upgrade()` must have a matching `downgrade()` that reverses it
2. Use `IF NOT EXISTS` / `IF EXISTS` guards for idempotency
3. Never modify existing migration files — always create new revisions
4. Test both upgrade and downgrade before committing
5. Each service's migrations are independent — no cross-service dependencies

## Adding Alembic to a New Service

1. Create the versions directory:
   ```bash
   mkdir -p microservices/<service>/alembic/versions
   ```

2. Create the initial migration:
   ```bash
   alembic -x service=<service> revision -m "initial schema"
   ```

3. Add your CREATE TABLE statements in `upgrade()` and DROP statements in `downgrade()`

4. Test:
   ```bash
   alembic -x service=<service> upgrade head
   alembic -x service=<service> downgrade -1
   alembic -x service=<service> upgrade head
   ```

## Environment Configuration

Database connection is built from environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | (empty) | Database password |
| `POSTGRES_DB` | `isa_platform` | Database name |

Load from environment files: `source deployment/environments/dev.env`
