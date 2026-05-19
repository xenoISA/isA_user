# artifact_service migrations

This directory contains the historical raw SQL migration files for the
`artifact` schema. They are preserved as the source of truth for the
schema design — the new **canonical** migration registry is Alembic,
under `microservices/artifact_service/alembic/versions/`.

## Files

| File | Purpose |
|------|---------|
| `001_create_artifact_tables.sql` | `artifacts` + `artifact_versions` + `artifact_shares` (Phase 1, #441) |
| `002_create_runtime_quota.sql` | `artifact_runtime_usage` per-day quota counter (Phase 3, #441) |
| `003_create_mcp_grants.sql` | `artifact_mcp_grants` MCP approval persistence (Phase 3, #441) |
| `004_create_artifact_kv.sql` | `artifact_kv` per-artifact namespaced storage (Phase 3, #441) |

Each SQL file is mirrored 1:1 by an Alembic revision in
`../alembic/versions/` with the same numeric prefix and an `art_*`
revision id (`art_001` … `art_004`).

## Upgrade path

### Dev

After bringing the service up locally either path is supported — the
raw `.sql` files remain the source of truth until Phase 2 (see below).

```bash
# Option A — Alembic (preferred for parity with prod)
cd /path/to/isA_user
PGPASSWORD=$POSTGRES_PASSWORD \
  alembic -x service=artifact_service upgrade head

# Option B — raw psql (legacy; still works)
for f in microservices/artifact_service/migrations/*.sql; do
  PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" \
      -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
done
```

The `-x service=artifact_service` flag is required for Alembic. Each
service gets its own `alembic_version_<service>` table so migration
history is tracked independently per service.

### Prod / staging

`alembic -x service=artifact_service upgrade head` is the deploy step,
run after new code is rolled out but before traffic shifts.

If the schema is already present (because earlier env. was applied via
`psql -f`), the first `upgrade head` will try to re-apply each
revision. Every revision in this service uses `IF NOT EXISTS` guards
plus FK CASCADE constraints, so re-application is a no-op on objects
that already exist. After it completes the
`alembic_version_artifact_service` row reflects `art_004`.

> If you would rather skip the no-op re-apply, stamp the version
> manually first:
>
> ```sql
> CREATE TABLE IF NOT EXISTS alembic_version_artifact_service (
>     version_num VARCHAR(32) NOT NULL PRIMARY KEY
> );
> INSERT INTO alembic_version_artifact_service (version_num)
> VALUES ('art_004')
> ON CONFLICT DO NOTHING;
> ```

### Rollback

```bash
alembic -x service=artifact_service downgrade -1
```

Every revision has a reversible `downgrade()`. CASCADE FKs from
`artifact_versions` / `artifact_shares` / `artifact_runtime_usage` /
`artifact_mcp_grants` / `artifact_kv` to `artifacts(id)` mean
downgrading `art_001` will sweep the child tables too — usually
desirable but worth noting before doing it in prod.

## Phase 2 (future)

Once Alembic adoption is proven stable across all services for one
release cycle, the raw `.sql` files will be retired (moved to
`migrations/legacy/`) and Alembic becomes the only path. Until then
they remain in tree as the schema-design source of truth.
