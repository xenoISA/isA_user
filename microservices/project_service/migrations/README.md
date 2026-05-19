# project_service migrations

This directory contains the historical raw SQL migration files for the
project_service schema. They are preserved for reference and as the source
of truth for the schema design — the new **canonical** migration registry
is Alembic, under `microservices/project_service/alembic/versions/`.

## Files

| File | Purpose |
|------|---------|
| `001_create_project_schema.sql` | Creates `project` schema + `projects` / `project_files` tables |
| `002_add_organization_scope.sql` | Adds `org_id` column and index |
| `003_add_star_archive_owner.sql` | Adds `owner_id`, `starred_at`, `archived_at` (story #442) |
| `004_backfill_owner_id.sql` | Backfills `owner_id` from `user_id`, drops `DEFAULT ''`, adds CHECK constraint (#463) |

Each SQL file is mirrored 1:1 by an Alembic revision in `../alembic/versions/`.
Going forward, **new schema changes ship as Alembic revisions only** — the
raw SQL files are frozen.

## Upgrade path

### Dev

After bringing the service up locally:

```bash
cd /path/to/isA_user
PGPASSWORD=$POSTGRES_PASSWORD \
  alembic -x service=project_service upgrade head
```

The `-x service=project_service` flag is required. Each service gets its own
`alembic_version_<service>` table so migration history is tracked
independently per service.

### Prod / staging

`alembic -x service=project_service upgrade head` is a deploy step,
run after the new code is rolled out but before traffic is shifted.

The backfill (004) is idempotent — it only touches rows where `owner_id` is
empty, so re-running is safe. After it completes:
- All existing rows have `owner_id` populated from their original `user_id`.
- The `DEFAULT ''` is removed; new inserts must specify `owner_id`.
- A CHECK constraint enforces `owner_id <> ''` at the DB level.

### Rollback

```bash
alembic -x service=project_service downgrade -1
```

Each revision has a reversible `downgrade()`. Note that `004` does **not**
un-backfill data on downgrade — backfilled values stay (they are correct),
the CHECK is dropped, and the `DEFAULT ''` is restored so the schema state
matches the post-003 shape.

## First Alembic adoption

This is the **first project_service Alembic adoption** in `isA_user`. Three
sibling services already use this pattern (`account_service`, `auth_service`,
`payment_service`). Remaining services still rely on the in-code
`_ensure_tables()` pattern or stand-alone SQL files; migrating them to
Alembic is tracked separately and is out of scope for #463.

> **Note**: This PR also includes a small fix to the shared `alembic/env.py`
> so the CLI actually resolves per-service version paths at command time
> (the prior scaffold only set `version_locations` after the CLI had already
> bound a `ScriptDirectory` — revisions were never discovered). The fix
> rebuilds `ScriptDirectory` and mutates the bound instance in place. This
> unblocks **all** services using the per-service Alembic pattern.
