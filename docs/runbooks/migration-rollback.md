# Migration Rollback Runbook

> Sibling docs: `deployment/helm/templates/migration-job.yaml`, `scripts/migrate.sh`, `.github/workflows/deploy.yml`.
> Issue: [#349](https://github.com/xenoISA/isA_user/issues/349) — Parent epic: [#345](https://github.com/xenoISA/isA_user/issues/345).

## What this covers

The platform runs a pre-deploy Kubernetes Job that executes
`scripts/migrate.sh upgrade all` as a Helm `pre-install,pre-upgrade` hook
before any service rollout. This runbook explains how to:

1. Inspect the migration Job and its logs.
2. Roll back a service's Alembic schema to a previous revision.
3. Recover the deploy after a partially-applied migration.
4. Stay inside the forward-only / backward-compatible migration policy.

## 1. Inspecting the migration Job

The CI workflow names the Helm release `isa-user-migrations`. The Job name is
suffixed with the unix epoch of the render and labelled
`app.kubernetes.io/name=isa-user-migrations`.

```bash
# Pick the namespace (staging vs production)
export NAMESPACE=isa-cloud-prod   # or isa-cloud-staging

# List recent migration Jobs (most recent last)
kubectl get jobs -n "$NAMESPACE" \
  -l app.kubernetes.io/name=isa-user-migrations \
  --sort-by=.metadata.creationTimestamp

# Tail logs of the most recent Job
JOB=$(kubectl get jobs -n "$NAMESPACE" \
  -l app.kubernetes.io/name=isa-user-migrations \
  --sort-by=.metadata.creationTimestamp \
  -o jsonpath='{.items[-1:].metadata.name}')
kubectl logs -n "$NAMESPACE" "job/$JOB"

# Or tail the running pod directly while it executes
POD=$(kubectl get pods -n "$NAMESPACE" \
  -l job-name="$JOB" -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n "$NAMESPACE" "$POD" --follow
```

The Job logs print, in order:
- All services it discovered (`scripts/migrate.sh list`)
- Pre-migration revisions (`scripts/migrate.sh status all`)
- The Alembic upgrade output (one block per service)
- Post-migration revisions
- Tracked raw SQL migration output (`scripts/migrate.sh sql-upgrade all`)

If the Job failed, its pod is preserved for debugging — `helm.sh/hook-delete-policy`
intentionally omits `hook-failed`. Cleanup happens automatically on the next
successful upgrade (`before-hook-creation`) or after `ttlSecondsAfterFinished`.

## 2. Manual Alembic rollback

Each service has its own version table (`alembic_version_<service>`) and its
own `microservices/<service>/alembic/versions/` directory. Roll back one
service at a time — never bulk-downgrade.

### From a developer workstation

```bash
# Configure the same DB env vars the Job uses
export POSTGRES_HOST=...   # from `kubectl get secret user-secrets -o yaml`
export POSTGRES_PORT=5432
export POSTGRES_DB=isa_platform
export POSTGRES_USER=...
export POSTGRES_PASSWORD=...

# Inspect current revision and history for a single service
bash scripts/migrate.sh status auth_service
alembic -x service=auth_service history --verbose

# Roll back ONE revision (most common — the last upgrade was bad)
bash scripts/migrate.sh downgrade auth_service -1

# Or roll back to a specific revision id
bash scripts/migrate.sh downgrade auth_service <revision-id>
```

### From inside the cluster (preferred for prod)

If you cannot reach Postgres from your workstation, run a one-shot pod that
inherits the same env as the migration Job. The simplest option is to spin
a debug pod with the same image and env spec:

```bash
# Spin a debug pod with the same image + env (uses the production values)
kubectl run alembic-debug \
  -n "$NAMESPACE" \
  --rm -it --restart=Never \
  --image="$(kubectl get job/$JOB -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}')" \
  --overrides="$(kubectl get job/$JOB -n $NAMESPACE -o json | jq '{spec: {containers: [.spec.template.spec.containers[0]]}}')" \
  --command -- /bin/bash

# Inside the pod:
bash scripts/migrate.sh status auth_service
bash scripts/migrate.sh downgrade auth_service -1
```

## 3. Recovering after a failed migration

A failed pre-deploy Job leaves the existing service replicas serving traffic
on the OLD code against whatever schema was applied so far. Three scenarios:

| Symptom | Action |
|---------|--------|
| Job failed before any DB writes (e.g., import error in migrate.sh) | Fix the bug, re-run the workflow. Old pods stayed serving the whole time. |
| Job failed mid-way (some services upgraded, some did not) | Read the logs, identify the last service that succeeded, manually downgrade that service if needed, then re-run the workflow. |
| Job succeeded but service rollout failed afterwards | The schema is already at HEAD. Roll back code via `kubectl rollout undo deployment/<svc>-deployment -n $NAMESPACE`. Old code MUST be backward-compatible with the new schema (see policy below). |

After fixing the underlying issue, re-trigger the deploy workflow. The Helm
hook deletion policy (`before-hook-creation`) ensures stale Jobs are
cleaned up before the new attempt.

## 4. Forward-only / backward-compatibility policy

Acceptance criterion from #349: *Backward-compat test — previous release version
reads new schema (no breaking column drops in single release).*

This is enforced as a process commitment, not a runtime check. Every PR that
touches `microservices/*/alembic/versions/` MUST follow these rules:

- **Additive changes only in a single release.** Add new columns nullable or
  with defaults; never `DROP COLUMN` or `ALTER COLUMN ... NOT NULL` in the
  same release that introduces the new app code that depends on it.
- **Two-phase removal.** To drop a column or rename a table, ship at least
  two releases:
  1. Release N: stop reading/writing the old column, keep the column.
  2. Release N+1: drop the column.
- **No destructive data migrations during the pre-deploy Job.** The Job has a
  600s `activeDeadlineSeconds` and `backoffLimit: 0` — it is for schema
  changes, not data backfills. Long-running data migrations belong in a
  dedicated one-shot Job triggered manually, post-deploy.
- **Test downgrade locally.** Before merging, run
  `bash scripts/migrate.sh upgrade <svc>` and `bash scripts/migrate.sh
  downgrade <svc> -1` against a local Postgres to verify the downgrade is
  non-destructive.
- **PR review checklist.** Reviewers MUST confirm the downgrade in the
  Alembic revision is implemented (not `pass`) and that the upgrade does
  not break the previous release's read path.

## 5. Quick reference — common commands

```bash
# Show every service's current revision
bash scripts/migrate.sh status all

# Apply pending migrations for one service
bash scripts/migrate.sh upgrade auth_service

# Roll back the last revision for one service
bash scripts/migrate.sh downgrade auth_service -1

# Re-run the entire migration Job manually (DOES NOT redeploy services)
helm upgrade --install isa-user-migrations ./deployment/helm \
  -f ./deployment/helm/values-production.yaml \
  --set migrationJob.image.tag=$VERSION \
  --namespace isa-cloud-prod \
  --wait --timeout 20m

# Disable the gate (emergency escape hatch — use only after a postmortem)
helm upgrade --install isa-user-migrations ./deployment/helm \
  -f ./deployment/helm/values-production.yaml \
  --set migrationJob.enabled=false \
  --namespace isa-cloud-prod
```

## See also

- `deployment/helm/templates/migration-job.yaml` — the Helm template
- `scripts/migrate.sh` — the runner the Job invokes
- `alembic/env.py` — per-service version table layout
- `.github/workflows/deploy.yml` — CI gate wiring
- Epic [#345](https://github.com/xenoISA/isA_user/issues/345) — HPA readiness context
