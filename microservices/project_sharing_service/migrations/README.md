# project_sharing_service migrations

This directory contains the historical raw SQL migration files for the
`project_sharing` schema. They are preserved as the source of truth
for the schema design — the new **canonical** migration registry is
Alembic, under `microservices/project_sharing_service/alembic/versions/`.

## Files

| File | Purpose |
|------|---------|
| `001_create_project_shares_table.sql` | `project_shares` + role/status enums (#442 / xenoISA/isA_#429) |

Each SQL file is mirrored 1:1 by an Alembic revision in
`../alembic/versions/` with the same numeric prefix and a `psharing_*`
revision id (`psharing_001`).

## Upgrade path

### Dev

After bringing the service up locally either path is supported — the
raw `.sql` file remains the source of truth until Phase 2 (see below).

```bash
# Option A — Alembic (preferred for parity with prod)
cd /path/to/isA_user
PGPASSWORD=$POSTGRES_PASSWORD \
  alembic -x service=project_sharing_service upgrade head

# Option B — raw psql (legacy; still works)
PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -f microservices/project_sharing_service/migrations/001_create_project_shares_table.sql
```

The `-x service=project_sharing_service` flag is required for Alembic.
Each service gets its own `alembic_version_<service>` table so
migration history is tracked independently per service.

### Prod / staging

`alembic -x service=project_sharing_service upgrade head` is the
deploy step, run after new code is rolled out but before traffic
shifts.

If the schema is already present (because earlier env. was applied via
`psql -f`), the first `upgrade head` will try to re-apply the
revision. The DDL uses `CREATE SCHEMA IF NOT EXISTS`, DO-block guards
around `CREATE TYPE` (Postgres has no IF NOT EXISTS for types), and
`CREATE TABLE IF NOT EXISTS`, so re-application is a no-op on objects
that already exist. After it completes the
`alembic_version_project_sharing_service` row reflects `psharing_001`.

> If you would rather skip the no-op re-apply, stamp the version
> manually first:
>
> ```sql
> CREATE TABLE IF NOT EXISTS alembic_version_project_sharing_service (
>     version_num VARCHAR(32) NOT NULL PRIMARY KEY
> );
> INSERT INTO alembic_version_project_sharing_service (version_num)
> VALUES ('psharing_001')
> ON CONFLICT DO NOTHING;
> ```

### Rollback

```bash
alembic -x service=project_sharing_service downgrade -1
```

The single revision's `downgrade()` drops the table, both enums, and
the schema (CASCADE). At this point there is no earlier revision to
downgrade to — `downgrade base` and `downgrade -1` are equivalent.

## Phase 2 (future)

Once Alembic adoption is proven stable across all services for one
release cycle, the raw `.sql` file will be retired (moved to
`migrations/legacy/`) and Alembic becomes the only path. Until then it
remains in tree as the schema-design source of truth.
