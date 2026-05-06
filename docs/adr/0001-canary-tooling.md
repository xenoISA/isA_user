# ADR 0001 — Canary Deploy Tooling: Argo Rollouts

> Status: Accepted (2026-05-04)
> Issue: [#350](https://github.com/xenoISA/isA_user/issues/350) — Parent epic: [#345](https://github.com/xenoISA/isA_user/issues/345)
> Sibling docs: `deployment/helm/templates/rollout.yaml`, `docs/runbooks/canary-deploy.md`

## Context

Epic #345 (K8s HPA Readiness) requires a canary deploy strategy for isA_user
microservices so a bad release does not reach 100% of traffic before metrics
catch up. Issue #350 specifies:

- Stage 1 replica → ≥60s health gate → 10% → 25% → 50% → 100% traffic ramp
- Auto-rollback on error rate >1% OR p95 latency >1.5× baseline
- Configurable Prometheus analysis queries
- Helm-native integration with the existing `deploy.yml` pipeline (already
  doing pre-deploy Alembic Jobs from #349 and a kubectl-driven blue/green
  step in production)

The platform already runs:

- Kubernetes (KIND for local, managed clusters for staging/prod)
- Helm 3 charts under `deployment/helm/`
- Consul + APISIX (no service mesh required)
- Prometheus for metrics (assumed present in the cluster)
- GitHub Actions CI (`/.github/workflows/deploy.yml`)

## Options considered

### Option A — Argo Rollouts (CHOSEN)

CRD-driven progressive delivery controller. Replaces `Deployment` with
`Rollout` (or wraps it). Native support for canary stages with traffic
weights, per-stage pauses, and analysis runs that hit Prometheus / Datadog /
New Relic / etc. Works without a service mesh by using the built-in
"basic canary" mode (replica-count-based traffic split via two Services and
a Pod-anti-affinity dance), and gains true L7 split when Istio / Linkerd /
SMI / Gateway API / Nginx / ALB are present.

Pros
- First-class Kubernetes object — `kubectl argo rollouts get rollout X`
  and a UI dashboard ship out of the box.
- Per-stage `pause` + `setWeight` directives match the issue spec verbatim.
- Inline `AnalysisTemplate` runs Prometheus queries during each step and
  aborts the rollout on threshold breach (== auto-rollback).
- Wide ecosystem adoption (CNCF Incubating). Documented for ArgoCD users
  who likely run the rest of the platform.
- Replicas-based canary works on a vanilla cluster — no mesh required to
  ship the first version.

Cons
- Adds a controller dependency in every cluster (one Deployment + CRDs).
- Replacing the existing `Deployment` shape touches every service chart.
  We mitigate by making rollout opt-in via `rollout.enabled` and shipping
  the `Rollout` template alongside the existing artefacts.

### Option B — Flagger

Operator that drives canary rollouts using Istio / Linkerd / Contour /
Gloo / NGINX / Skipper / Traefik / ALB. Uses the same primitives (steps,
analysis, metric queries).

Pros
- Production-grade, similar feature set.
- Tighter integration with service meshes when one exists.

Cons
- **Hard requirement on a service-mesh or supported ingress for traffic
  splitting.** isA_user fronts traffic with APISIX, which Flagger does not
  list as a first-class provider — we'd need to migrate to a supported
  mesh first.
- Pause/promote workflow is less visible (no dedicated dashboard /
  `kubectl` plugin equivalent to Argo's).

### Option C — Custom (kubectl + Bash + Prometheus queries in CI)

Bake the canary loop into `deploy.yml` itself: scale a canary Deployment,
sleep 60s, query Prometheus, scale up, repeat.

Pros
- No new cluster dependencies.
- Logic is auditable in the workflow file.

Cons
- Reinvents Argo Rollouts poorly. State lives in the runner, so a CI cancel
  abandons the canary mid-stage. No UI, no `kubectl` introspection, no
  experiments / blue-green / preview environments later. Operators who want
  to "pause" or "promote" manually have nothing to drive.
- Multiplies code in the workflow per service.

## Decision

**Adopt Argo Rollouts.** It is the only option that satisfies the issue
acceptance criteria with reasonable operational effort and zero forced
dependencies on a service mesh. The basic canary mode is sufficient for
the first cut; we keep the door open to plug in APISIX or a mesh later
purely by editing the `Rollout` `strategy.canary.trafficRouting` block.

## Consequences

### Positive

- Stages and analysis are declarative inside the chart — diffs in git
  show the full canary policy.
- `kubectl argo rollouts get rollout user-auth-service -n isa-cloud-prod`
  gives operators a live tree view during every deploy.
- Re-using the existing migration-job hook order: Alembic Job (pre-upgrade
  hook) runs to completion → service `Rollout` reconciles → analysis
  template promotes or aborts.
- Production stays on canary; staging keeps the simpler kubectl-driven
  rollout (faster feedback for developers) by toggling
  `rollout.enabled=false` in `values-staging.yaml`.

### Negative / Follow-ups

- Cluster admins MUST install the Argo Rollouts controller before this
  chart's `Rollout` resource can reconcile. See the runbook for the
  install command and link to the upstream guide.
- The shared `isa-service` chart in isA_Cloud still renders a
  `Deployment` for each service. We deliberately ship the `Rollout` as
  a sibling resource rather than mutating that chart in this PR — see
  the runbook section "Migration path from Deployment to Rollout" for
  how an operator hands traffic over.
- We do not yet have a service mesh; traffic-splitting fidelity is
  approximate (replica-count weighted). For the spec's 10/25/50/100
  thresholds this is acceptable because we are still gating each step on
  a Prometheus analysis run.

## Links

- Argo Rollouts docs: https://argo-rollouts.readthedocs.io/
- Install: `kubectl create namespace argo-rollouts && kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml`
- Flagger comparison: https://argo-rollouts.readthedocs.io/en/stable/FAQ/#how-does-argo-rollouts-differ-from-flagger
