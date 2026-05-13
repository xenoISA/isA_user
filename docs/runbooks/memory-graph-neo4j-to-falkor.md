# Memory Graph Neo4j-to-Falkor Backfill Runbook

> Issue: [#395](https://github.com/xenoISA/isA_user/issues/395). Parent epic: [#392](https://github.com/xenoISA/isA_user/issues/392).

## Decision

Do not build or run a Neo4j-to-FalkorDB backfill unless an environment audit
finds legacy memory graph data in Neo4j.

The runtime path already reads memory graph data through isA_Data/FalkorDB. This
runbook exists for the optional one-shot legacy data path only.

## Audit First

Run the audit in each environment that still has a Neo4j deployment:

```bash
python scripts/audit_memory_graph_backfill.py \
  --namespace isa-cloud-staging \
  --pod neo4j-0 \
  --password "$NEO4J_PASSWORD"

python scripts/audit_memory_graph_backfill.py \
  --namespace isa-cloud-production \
  --pod neo4j-0 \
  --password "$NEO4J_PASSWORD"
```

The script is read-only. It executes:

- `MATCH (n) RETURN count(n)`
- `MATCH (n) WHERE n:<memory label> ... RETURN count(n)`
- `MATCH ()-[r]->() RETURN count(r)`

Exit codes:

- `0`: no memory graph nodes found; no backfill required.
- `2`: memory graph nodes found; prepare a dedicated backfill job before cutover.
- non-zero other: audit failed; fix credentials/connectivity and rerun.

## Local Evidence

On 2026-05-13, the local `kind-isa-cloud-local` context, `neo4j-0` in
`isa-cloud-local`, returned:

```json
{
  "backfill_required": false,
  "checked_at": "2026-05-13T06:37:03.863864+00:00",
  "database": "neo4j",
  "memory_nodes": 0,
  "namespace": "isa-cloud-local",
  "pod": "neo4j-0",
  "relationship_count": 0,
  "total_nodes": 0
}
```

This proves the local cluster has no legacy Neo4j graph data to backfill. This
does not prove staging or production are empty; those environments must be
audited from a context with access to their namespaces.

## If Audit Finds Data

Create a separate migration issue and implement a one-shot Kubernetes Job with:

- Read-only Neo4j source credentials.
- FalkorDB destination credentials.
- Idempotent upserts keyed by stable memory/entity ids.
- Batch checkpoints and dry-run mode.
- Parity checks comparing node counts, relationship counts, and sampled
  graph-search responses between source and destination.

Do not put this data backfill into the normal Alembic/Helm pre-deploy migration
job. It is operational data movement, not a schema migration.

## If Audit Finds No Data

Attach the JSON audit output to #395 and close the issue as not needed. No
runtime code change is required.
