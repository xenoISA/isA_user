# memory_service migrations

This directory contains the historical raw SQL migration files for the
`memory` schema. They are preserved as the source of truth for the
schema design — the new **canonical** migration registry is Alembic,
under `microservices/memory_service/alembic/versions/`.

## Files

| File | Purpose |
|------|---------|
| `000_init_schema.sql` | Creates `memory` schema + shared `update_updated_at()` trigger fn |
| `001_create_factual_memories_table.sql` | Subject/predicate/object facts |
| `002_create_episodic_memories_table.sql` | Personal events with spatial/temporal context |
| `003_create_procedural_memories_table.sql` | Stepwise how-to / skill memories |
| `004_create_semantic_memories_table.sql` | Concepts/definitions and general knowledge |
| `005_create_working_memories_table.sql` | TTL-scoped task scratchpad |
| `006_create_session_memories_table.sql` | Conversation context + session_summaries |
| `007_create_memory_metadata_table.sql` | Usage/quality/lifecycle sidecar |
| `008_create_memory_associations_table.sql` | Source ↔ target relationship mapping |
| `009_create_memory_functions.sql` | `track_memory_access()` + metadata triggers |
| `010_create_memory_state_table.sql` | `user_memory_state` (pause/reset audit — #428 / #439) |
| `011_create_memory_summaries_table.sql` | `memory_summaries` narrative table (#428 hard slice / #439) |

Each SQL file is mirrored 1:1 by an Alembic revision in
`../alembic/versions/` with the same numeric prefix and a `mem_*`
revision id (`mem_000` … `mem_011`).

## Upgrade path

### Dev

After bringing the service up locally either path is supported — the
raw `.sql` files remain the source of truth until Phase 2 (see below).

```bash
# Option A — Alembic (preferred for parity with prod)
cd /path/to/isA_user
PGPASSWORD=$POSTGRES_PASSWORD \
  alembic -x service=memory_service upgrade head

# Option B — raw psql (legacy; still works)
for f in microservices/memory_service/migrations/*.sql; do
  PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" \
      -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$f"
done
```

The `-x service=memory_service` flag is required for Alembic. Each
service gets its own `alembic_version_<service>` table so migration
history is tracked independently per service.

### Prod / staging

`alembic -x service=memory_service upgrade head` is the deploy step,
run after new code is rolled out but before traffic shifts.

If the schema is already present (because earlier env. was applied via
`psql -f`), the first `upgrade head` is **not** auto-stamped — Alembic
will try to re-apply each revision. Every revision in this service
uses `IF NOT EXISTS` / DO-block guards, so re-application is a no-op
on tables/indexes/triggers that already exist. After it completes the
`alembic_version_memory_service` row reflects `mem_011`.

> If you would rather skip the no-op re-apply (e.g. on a hot prod
> table that you want zero DDL noise against), stamp the version
> manually first:
>
> ```sql
> CREATE TABLE IF NOT EXISTS alembic_version_memory_service (
>     version_num VARCHAR(32) NOT NULL PRIMARY KEY
> );
> INSERT INTO alembic_version_memory_service (version_num)
> VALUES ('mem_011')
> ON CONFLICT DO NOTHING;
> ```

### Rollback

```bash
alembic -x service=memory_service downgrade -1
```

Every revision has a reversible `downgrade()`. Note that
`009_create_memory_functions` (`mem_009`) drops the triggers and the
plpgsql helper functions but does not unwind metadata rows already
written into `memory.memory_metadata` — those values stay (they are
correct), the trigger is detached, and re-applying the revision is a
no-op.

## Phase 2 (future)

Once Alembic adoption is proven stable across all services for one
release cycle, the raw `.sql` files will be retired (moved to
`migrations/legacy/`) and Alembic becomes the only path. Until then
they remain in tree as the schema-design source of truth.
