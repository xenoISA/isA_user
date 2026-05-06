# ADR 0001 — HPA custom-metrics tooling: KEDA over Prometheus Adapter

- **Status**: Accepted
- **Date**: 2026-05-04
- **Author**: isA_user platform team
- **Issue**: [#352](https://github.com/xenoISA/isA_user/issues/352) — Parent epic: [#345](https://github.com/xenoISA/isA_user/issues/345)
- **Supersedes**: n/a (first ADR for the K8s HPA readiness workstream)

## Context

Today's HorizontalPodAutoscalers in `deployment/helm/values-production.yaml` scale
on CPU 70% / memory 80% only:

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilization: 70
  targetMemoryUtilization: 80
```

That is generic and lags real load for our 35-service mix:

- **Event consumers** (`wallet`, `billing`, `payment`) burn very little CPU per
  message but accumulate NATS JetStream backlog under burst — they need to
  scale on **queue depth**, not CPU.
- **Auth-heavy services** (`auth`, `account`, `authorization`) tail-latency-spike
  long before CPU saturates because the bottleneck is downstream
  Postgres/Redis fan-out. They need to scale on **p95 request latency**.
- **Telemetry / streaming** (`telemetry`, `notification`) hold long-lived
  WebSocket connections; CPU/memory per pod is flat regardless of fan-out, so
  scaling has to track **connection count or message rate**.

Two viable options exist on a vanilla Kubernetes cluster:

1. **Prometheus Adapter** (`k8s-prometheus-adapter`) — registers a custom
   `external.metrics.k8s.io` API backed by PromQL queries. The `HPA` resource
   then references the metric directly.
2. **KEDA** (Kubernetes Event-Driven Autoscaler) — installs a controller that
   reconciles `ScaledObject` CRs into HPAs. Ships a built-in scaler library
   (NATS, Kafka, Prometheus, Redis Streams, RabbitMQ, AWS SQS, …).

## Decision

**Adopt KEDA as the primary autoscaling controller for the platform.**

Helm renders `ScaledObject` resources (one per service that opts in) when
`hpa.enabled=true`. Each `ScaledObject` declares one or more triggers; KEDA
synthesises the underlying HPA. CPU and memory triggers are kept on every
`ScaledObject` as fallback ceilings so a pod with a stuck custom-metric
collector still scales on raw load.

## Alternatives considered

### Prometheus Adapter

- Pros: single dependency we already need in some form (we run Prometheus
  for SLOs), no new CRD surface, HPA is the native object.
- Cons:
  - **No native NATS scaler.** Queue depth would need to be exported to
    Prometheus first (extra exporter, extra scrape latency, extra failure
    mode). This is the load shape that *most* needs custom autoscaling for
    `wallet`/`billing`/`payment`, so degrading it is a non-starter.
  - PromQL strings live in a `ConfigMap` that the adapter parses on start —
    debugging a misnamed metric requires a controller restart.
  - One adapter Deployment is a single point of failure for *every* HPA on
    the cluster. KEDA controllers are stateless and scale horizontally.

### Stay on CPU/memory only

- Pros: zero new infra.
- Cons: doesn't satisfy issue #352 acceptance criteria; we already know from
  the discover audit that CPU saturates *after* SLA breach for both event
  consumers and auth services.

## Consequences

### Positive

- One controller covers all three load shapes:
  - NATS JetStream depth (`nats_jetstream_consumer_pending_messages`-equivalent
    via the built-in `nats-jetstream` scaler).
  - Prometheus queries (p95 latency, WS connection gauge) via the
    `prometheus` scaler — same PromQL we'd write for the adapter, no
    `ConfigMap` indirection.
  - CPU/memory via `cpu` and `memory` triggers — KEDA delegates to the
    upstream HPA resource metrics so behaviour is identical to today.
- `ScaledObject`s declare `idleReplicaCount`/`minReplicaCount`/`maxReplicaCount`
  in one place, replacing the parallel HPA+manual scale-to-zero scripts.
- `advanced.horizontalPodAutoscalerConfig.behavior` lets us pin scale-down
  windows per service tier (auth services tolerate more aggressive
  scale-down than wallet, where queue spikes mid-drain are common).

### Negative / cost

- KEDA controller and metrics-apiserver must be installed cluster-wide
  (`keda` namespace). **This Helm chart does not install KEDA.** The cluster
  operator runs `helm install keda kedacore/keda -n keda --create-namespace`
  before the first `helm upgrade` of an isA_user service that has
  `hpa.enabled=true`. Documented in `docs/runbooks/hpa-metrics.md`.
- New CRDs (`scaledobjects.keda.sh`, `triggerauthentications.keda.sh`) on
  the cluster. Backwards-compatible: removing KEDA returns services to
  manual replica counts.
- `prometheus` triggers depend on a reachable Prometheus endpoint
  (`http://prometheus.isa-cloud-prod:9090`). If a Prometheus exporter for a
  required signal does not exist yet (e.g. WebSocket connection gauge for
  `telemetry_service`), the trigger is left commented in
  `values-production.yaml` and a follow-up issue is opened — this ADR does
  not authorise adding new exporters to service code.

### Rollback

Setting `hpa.enabled=false` (or `services.<name>.hpa.enabled=false`) in
`values-*.yaml` causes the chart to skip rendering the `ScaledObject`. KEDA
deletes the underlying HPA and the Deployment returns to its
`spec.replicas` value. No data path change.

## Validation

- `helm lint deployment/helm/ --strict` — passes with `hpa.enabled` toggled
  on and off.
- `helm template deployment/helm/ -f deployment/helm/values-production.yaml
  --set hpa.enabled=true` — emits one `ScaledObject` per opted-in service
  with the correct trigger list.
- The runbook `docs/runbooks/hpa-metrics.md` documents per-service rationale
  and how to tune thresholds.

## References

- Issue #352 (this ADR's authorising work item).
- Parent epic #345 — K8s HPA readiness.
- KEDA scaler catalogue: <https://keda.sh/docs/latest/scalers/>
- Prometheus Adapter: <https://github.com/kubernetes-sigs/prometheus-adapter>
- Kubernetes HPA `behavior` field:
  <https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/#configurable-scaling-behavior>
