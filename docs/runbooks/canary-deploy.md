# Canary Deploy Runbook

> Sibling docs: `deployment/helm/templates/rollout.yaml`,
> `deployment/helm/templates/analysis-template.yaml`,
> `docs/adr/0001-canary-tooling.md`,
> `.github/workflows/deploy.yml`.
>
> Issue: [#350](https://github.com/xenoISA/isA_user/issues/350) —
> Parent epic: [#345](https://github.com/xenoISA/isA_user/issues/345).
> Tooling: Argo Rollouts.

## What this covers

The platform progresses every production deploy through an Argo Rollouts
canary ladder. This runbook explains how to:

1. Verify the controller is installed in the target cluster.
2. Watch a canary in flight.
3. Manually promote, pause, abort, or roll back.
4. Read the AnalysisRun output when auto-rollback fires.
5. Migrate a service from the legacy `Deployment` to the new `Rollout`.

If you are looking for the migration-Job pre-deploy gate, see
`docs/runbooks/migration-rollback.md` instead — that runs FIRST, before
any canary starts.

## 0. Prerequisites — install the controller

The chart renders `Rollout` and `AnalysisTemplate` CRs but does NOT
install the Argo Rollouts controller itself. Install it once per
cluster:

```bash
kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts \
  -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Optional but strongly recommended — kubectl plugin for live tree views.
brew install argoproj/tap/kubectl-argo-rollouts   # macOS
# or download the binary from
#   https://github.com/argoproj/argo-rollouts/releases/latest
```

Upstream install guide:
<https://argo-rollouts.readthedocs.io/en/stable/installation/>.

Verify:

```bash
kubectl get crd rollouts.argoproj.io analysistemplates.argoproj.io
kubectl get pods -n argo-rollouts
kubectl argo rollouts version
```

## 1. Trigger a canary deploy

The CI workflow (`.github/workflows/deploy.yml`) handles this for you.
Push a tag (`v*`) or run the `Deploy` workflow with `environment=production`.

Sequence:

1. `prepare` resolves environment, services, version.
2. `build` pushes images to GHCR.
3. `deploy-production` -> `Pre-deploy schema migration gate` runs the
   Alembic Job (helm pre-upgrade hook). Existing replicas keep serving
   until this Job exits 0.
4. `deploy-production` -> `Canary Rollout` updates the image on every
   service `Rollout` CR. Argo takes over from there.

Manual trigger for a single service (debugging):

```bash
NAMESPACE=isa-cloud-prod
SERVICE=user-auth-service
VERSION=v1.4.2

kubectl argo rollouts set image "${SERVICE}" \
  "${SERVICE}=ghcr.io/xenoisa/isa_user/${SERVICE#user-}:${VERSION}" \
  -n "${NAMESPACE}"
```

## 2. Watch a canary in flight

```bash
NAMESPACE=isa-cloud-prod
SERVICE=user-auth-service

# Live tree view — best single command for situational awareness.
kubectl argo rollouts get rollout "${SERVICE}" -n "${NAMESPACE}" --watch

# Just the current step / weight / status:
kubectl argo rollouts status "${SERVICE}" -n "${NAMESPACE}"

# Inspect AnalysisRuns triggered during the canary.
kubectl get analysisrun -n "${NAMESPACE}" \
  -l rollout="${SERVICE}"  --sort-by=.metadata.creationTimestamp
```

The tree view shows:

- The stable + canary ReplicaSets (with hashes).
- Current step index and target weight.
- Analysis pass/fail per metric.
- Time spent paused.

Default ramp from issue #350 (rendered by `templates/rollout.yaml`):

| Step | Action            | Notes                              |
|------|-------------------|------------------------------------|
| 0    | setCanaryScale=1  | Pin canary at exactly one replica. |
| 1    | pause 60s         | Health gate.                       |
| 2    | matchTrafficWeight| Release the pin.                   |
| 3    | setWeight 10      |                                    |
| 4    | analysis          | error-rate + p95 ratio.            |
| 5    | pause 30s         | Drain analysis window.             |
| 6    | setWeight 25      |                                    |
| 7    | analysis          |                                    |
| 8    | pause 30s         |                                    |
| 9    | setWeight 50      |                                    |
| 10   | analysis          |                                    |
| 11   | pause 30s         |                                    |
| —    | implicit 100%     | Argo promotes after final step.    |

## 3. Manual gates — promote, pause, abort, retry

```bash
NAMESPACE=isa-cloud-prod
SERVICE=user-auth-service

# Promote past the current step (skips remaining time on a pause).
kubectl argo rollouts promote "${SERVICE}" -n "${NAMESPACE}"

# Promote past ALL remaining steps (jump straight to 100%). Use with care.
kubectl argo rollouts promote "${SERVICE}" -n "${NAMESPACE}" --full

# Abort — Argo halts the canary and routes 100% back to the stable RS.
# Stable pods continue serving; canary RS is scaled down per
# scaleDownDelaySeconds (default 60 in production).
kubectl argo rollouts abort "${SERVICE}" -n "${NAMESPACE}"

# Retry an aborted rollout (re-runs from step 0).
kubectl argo rollouts retry rollout "${SERVICE}" -n "${NAMESPACE}"
```

Pausing with no time bound:

```bash
# Indefinite pause (no duration). Use to investigate before promoting.
kubectl argo rollouts pause "${SERVICE}" -n "${NAMESPACE}"
```

## 4. Auto-rollback — what just happened?

When a Prometheus metric breaches threshold, the AnalysisRun fails and
Argo aborts the rollout automatically. Symptoms:

```bash
$ kubectl argo rollouts status user-auth-service -n isa-cloud-prod
Status: Degraded
Message: RolloutAborted: Rollout aborted update to revision 12: ...
```

Investigate:

```bash
NAMESPACE=isa-cloud-prod
SERVICE=user-auth-service

# Latest AnalysisRun for this service.
RUN=$(kubectl get analysisrun -n "${NAMESPACE}" \
  -l rollout="${SERVICE}" \
  --sort-by=.metadata.creationTimestamp \
  -o jsonpath='{.items[-1:].metadata.name}')

kubectl describe analysisrun "${RUN}" -n "${NAMESPACE}" | sed -n '/Status:/,$p'

# Per-metric measurements (the actual Prometheus values that failed).
kubectl get analysisrun "${RUN}" -n "${NAMESPACE}" \
  -o jsonpath='{.status.metricResults}' | jq .
```

Common causes:

| Symptom                                  | Likely root cause                              |
|------------------------------------------|------------------------------------------------|
| `error-rate` failed, `result[0]` ≈ 1.0   | Misconfig, exception loop, bad migration tail. |
| `latency-p95-ratio` > 1.5                | Cold cache, GC churn, downstream slowdown.     |
| `query did not return any results`       | New label drift — check Prometheus targets.    |
| Both metrics passing but rollout stuck   | A `pause` step with no duration — promote it.  |

After triage, redeploy the previous good version (auto-rollback only
halts traffic; image rollback is manual):

```bash
# Show recent revisions (image SHAs).
kubectl argo rollouts history rollout "${SERVICE}" -n "${NAMESPACE}"

# Roll back to the previous revision (re-runs the canary ladder).
kubectl argo rollouts undo "${SERVICE}" -n "${NAMESPACE}"
```

## 5. Tweaking thresholds for one service

Edit `deployment/helm/values-production.yaml`:

```yaml
rollout:
  enabled: true
  healthGateSeconds: 120        # bake the canary longer
  analysis:
    errorRateThreshold: "0.005" # tighter — 0.5% triggers rollback
    latencyRatioThreshold: "1.3"
```

For service-specific overrides, ship a second values-prod-<service>.yaml
or override at the CLI:

```bash
helm upgrade --install isa-user-rollout deployment/helm/ \
  -f deployment/helm/values-production.yaml \
  --set rollout.enabled=true \
  --set rollout.analysis.errorRateThreshold="0.005" \
  -n isa-cloud-prod
```

## 6. Migration path from Deployment to Rollout

The shared `isa-service` chart in `isA_Cloud` still renders a
`Deployment` per service. The new `Rollout` resource ships from the
`isA_user` chart. Two controllers cannot own the same Pods. Hand
ownership over once per service:

```bash
NAMESPACE=isa-cloud-prod
SERVICE=user-auth-service

# 1. Apply the Rollout chart (Rollout starts at replicas=2).
helm upgrade --install isa-user-rollout deployment/helm/ \
  -f deployment/helm/values-production.yaml \
  -n "${NAMESPACE}"

# 2. Wait for the Rollout's pods to be Healthy (`Available` == replicas).
kubectl argo rollouts get rollout "${SERVICE}" -n "${NAMESPACE}" --watch
# Press Ctrl-C once Status: Healthy.

# 3. Drain the legacy Deployment by scaling to 0.
kubectl scale deployment "${SERVICE}" --replicas=0 -n "${NAMESPACE}"

# 4. Verify Service endpoints flipped to the Rollout pods.
kubectl get endpoints "${SERVICE}" -n "${NAMESPACE}" -o yaml | head -40

# 5. Once stable for ≥1 release cycle, delete the legacy Deployment.
kubectl delete deployment "${SERVICE}" -n "${NAMESPACE}"
```

To revert (canary tooling broken, controller down, etc.):

```bash
# Disable rollout rendering.
helm upgrade --install isa-user-rollout deployment/helm/ \
  -f deployment/helm/values-production.yaml \
  --set rollout.enabled=false \
  -n "${NAMESPACE}"

# Bring the legacy Deployment back online.
kubectl scale deployment "${SERVICE}" --replicas=2 -n "${NAMESPACE}"
```

## 7. CI-side knobs

`.github/workflows/deploy.yml` exposes these inputs that interact with
the canary:

- `services` — comma-separated list. The `Canary Rollout` step iterates
  exactly this list, so you can canary one service in isolation while
  the others stay on their stable image.
- `environment=production` — the canary path. `staging` keeps the
  simpler `kubectl set image` step (`rollout.enabled: false`).

The workflow does NOT block on canary completion by default — Argo
takes minutes-to-hours depending on the ramp. The `Canary Rollout`
step uses `kubectl argo rollouts status --watch --timeout=30m` to
fail the workflow on auto-rollback while still surfacing live progress
in the run logs.
