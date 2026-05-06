# HPA Limits & Per-Service Capacity Plan

> **Status**: Initial baseline — numbers below reflect the **default Helm values**
> applied uniformly to every service. p95 memory and per-service tuning are
> TODOs that need staging measurements before they can be tightened.
>
> **Related**: Epic [#345](https://github.com/xenoISA/isA_user/issues/345) (K8s HPA readiness),
> Issue [#346](https://github.com/xenoISA/isA_user/issues/346) (Postgres pool budget remediation),
> Issue [#347](https://github.com/xenoISA/isA_user/issues/347) (Redis caching),
> Issue [#353](https://github.com/xenoISA/isA_user/issues/353) (this doc),
> [`docs/prd/k8s_hpa_readiness.md`](../prd/k8s_hpa_readiness.md) (PRD).

## Sources of Truth

| Setting                | Source                                                       |
| ---------------------- | ------------------------------------------------------------ |
| Service tier           | [`deployment/local-dev.sh`](../../deployment/local-dev.sh) (`TIER{1..4}_SERVICES`) |
| Canonical service list | [`config/ports.yaml`](../../config/ports.yaml) (`microservices:` block) |
| Helm replicas / HPA    | [`deployment/helm/values-production.yaml`](../../deployment/helm/values-production.yaml) |
| Pool sizing            | [`core/postgres_client.py`](../../core/postgres_client.py) (`PG_MIN_POOL_SIZE` / `PG_MAX_POOL_SIZE`) |
| Helm chart template    | `isA_Cloud/deployments/charts/isa-service` (external)        |

## Default Helm Production Values

These values apply to **every service** today — there are no per-service overrides
in `values-production.yaml`. If/when overrides are added, update this doc
alongside the values change.

| Setting                  | Value      | Notes                                           |
| ------------------------ | ---------- | ----------------------------------------------- |
| `replicas`               | `2`        | Initial replica count before HPA takes over     |
| `autoscaling.enabled`    | `true`     | HPA enabled for all services                    |
| `autoscaling.minReplicas`| `2`        | Floor                                           |
| `autoscaling.maxReplicas`| `10`       | Ceiling                                         |
| `targetCPUUtilization`   | `70%`      |                                                 |
| `targetMemoryUtilization`| `80%`      |                                                 |
| `resources.requests.memory` | `512Mi` |                                                 |
| `resources.limits.memory`   | `1Gi`   |                                                 |
| `resources.requests.cpu`    | `250m`  |                                                 |
| `resources.limits.cpu`      | `1000m` |                                                 |
| `PG_MIN_POOL_SIZE` (per pod) | `1`    | Minimum asyncpg pool size                       |
| `PG_MAX_POOL_SIZE` (per pod) | `2`    | Maximum asyncpg pool size                       |

**Pool sizing comment from `core/postgres_client.py:85`:**

> "Pool sizing: with 35 microservices sharing PG max_connections=100, each
> service gets at most 2 connections (35×2=70, under the 100 limit)."
>
> **NOTE**: That comment assumes **1 pod per service**. With HPA min=2 and
> max=10, the actual ceiling math is very different. See
> [Postgres connection budget](#postgres-connection-budget) below.

## Per-Service Breakdown

Tiers come from `deployment/local-dev.sh` (3 + 8 + 5 + 19 = **35 tiered
services**). "Untiered" services are present on disk (and possibly in
`config/ports.yaml`) but not assigned to any `TIER*_SERVICES` list in
`local-dev.sh` — they need to be classified (TODO). The two untiered
services today are `sharing_service` and `project_service`, bringing the
total inventory to **35 tiered + 2 untiered = 37**. See
[Untiered / Missing-from-Helm services](#untiered--missing-from-helm-services)
for the canonical inventory drift table.

Bottleneck column is a coarse first-cut hypothesis based on service shape;
needs validation in staging.

| # | Service               | Tier | k8s name             | Port | HPA min/max | Pool min→max (1 pod) | Pool min→max (HPA min: 2 pods) | Pool min→max (HPA max: 10 pods) | Memory request → limit | p95 memory | Likely first bottleneck |
|---|-----------------------|------|----------------------|------|-------------|----------------------|--------------------------------|---------------------------------|------------------------|------------|-------------------------|
|  1 | auth_service          | 1    | user-auth            | 8201 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool (login bursts), CPU (bcrypt) |
|  2 | account_service       | 1    | user-account         | 8202 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
|  3 | organization_service  | 1    | user-organization    | 8212 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
|  4 | session_service       | 2    | user-session         | 8203 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | Redis (hot path)        |
|  5 | authorization_service | 2    | user-authorization   | 8204 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool, NATS (RBAC events) |
|  6 | wallet_service        | 2    | user-wallet          | 8208 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool (txns), NATS    |
|  7 | memory_service        | 2    | user-memory          | 8223 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | Memory (embeddings), Qdrant |
|  8 | storage_service       | 2    | user-storage         | 8209 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | MinIO bandwidth, memory (uploads) |
|  9 | event_service         | 2    | user-event           | 8230 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | NATS subs               |
| 10 | audit_service         | 2    | user-audit           | 8205 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool (write-heavy)   |
| 11 | notification_service  | 2    | user-notification    | 8206 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | External APIs, NATS subs |
| 12 | billing_service       | 3    | user-billing         | 8216 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool (usage events), NATS subs |
| 13 | subscription_service  | 3    | user-subscription    | 8228 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 14 | product_service       | 3    | user-product         | 8215 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 15 | telemetry_service     | 3    | user-telemetry       | 8225 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool (write-heavy ingest) |
| 16 | vault_service         | 3    | user-vault           | 8214 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | CPU (encrypt/decrypt)   |
| 17 | payment_service       | 4    | user-payment         | 8207 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | External (Stripe), DB pool |
| 18 | order_service         | 4    | user-order           | 8210 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 19 | task_service          | 4    | user-task            | 8211 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | NATS subs               |
| 20 | calendar_service      | 4    | user-calendar        | 8217 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 21 | weather_service       | 4    | user-weather         | 8218 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | External API, Redis cache |
| 22 | album_service         | 4    | user-album           | 8219 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 23 | device_service        | 4    | user-device          | 8220 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool, MQTT           |
| 24 | ota_service           | 4    | user-ota             | 8221 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | MinIO, DB pool          |
| 25 | media_service         | 4    | user-media           | 8222 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | Memory (transcoding), MinIO |
| 26 | location_service      | 4    | user-location        | 8224 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 27 | compliance_service    | 4    | user-compliance      | 8226 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 28 | document_service      | 4    | user-document        | 8227 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | MinIO, DB pool          |
| 29 | credit_service        | 4    | user-credit          | 8229 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 30 | invitation_service    | 4    | user-invitation      | 8213 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 31 | membership_service    | 4    | user-membership      | 8250 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 32 | campaign_service      | 4    | user-campaign        | 8251 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 33 | inventory_service     | 4    | user-inventory       | 8252 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool (reservations)  |
| 34 | tax_service           | 4    | user-tax             | 8253 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | External API, DB pool   |
| 35 | fulfillment_service   | 4    | user-fulfillment     | 8254 | 2 / 10      | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi            | TODO       | DB pool                 |
| 36 | sharing_service       | untiered | user-sharing     | 8255 | 2 / 10*     | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi*           | TODO       | DB pool                 |
| 37 | project_service       | untiered | user-project     | 8260 | 2 / 10*     | 1 → 2                | 2 → 4                          | 10 → 20                         | 512Mi → 1Gi*           | TODO       | DB pool                 |

\* `sharing_service` is listed in `config/ports.yaml` (port `8255`, k8s
`user-sharing`) but **is not in any tier in `deployment/local-dev.sh`** and
**is not in `deployment/helm/values-production.yaml`** — so it is not part of
the standard rollout today. The row above shows the default-if-deployed
values.

\* `project_service` exists on disk (`microservices/project_service/`, port
`8260` hard-coded in its `main.py`) but **is not in `config/ports.yaml`**,
**is not in any tier in `deployment/local-dev.sh`**, and **is not in
`deployment/helm/values-production.yaml`** — so it is not part of the
standard rollout today. The row above shows the default-if-deployed values
and assumes the same `user-project` k8s name and port `8260` would be used
once it is registered. A tiering decision (probably Tier 2 based on its
dependencies) is still needed.

## Postgres Connection Budget

> **REDLINE: This is the gap that issue [#346](https://github.com/xenoISA/isA_user/issues/346) exists to close.**

`max_pool_size` is **per pod**, so connection demand scales with replicas.

### Math

The `services_in_helm = 35` figure is the count of services actually deployed
via Helm today (entries under `services:` in
`deployment/helm/values-production.yaml`). The 140 / 700 connection counts
below describe **only those 35 services**. The two untiered services exist
on disk but are not in `values-production.yaml`: `sharing_service` is in
`config/ports.yaml` but missing from `local-dev.sh`, and `project_service`
is missing from `config/ports.yaml`, `local-dev.sh`, and Helm. If both were
deployed under the same defaults, the totals would rise to 148 / 740 — see
the second block below.

```
connections_per_pod      = PG_MAX_POOL_SIZE = 2
pods_per_service_at_min  = HPA.minReplicas  = 2     → 4 connections per service
pods_per_service_at_max  = HPA.maxReplicas  = 10    → 20 connections per service

# Services actually deployed via Helm today
services_in_helm = 35      (entries in deployment/helm/values-production.yaml)
connections_at_min_replicas = 35 × 4   = 140
connections_at_max_replicas = 35 × 20  = 700

# Adding the 2 currently-untiered / not-in-Helm services
services_total   = 37      (35 in Helm + project_service + sharing_service)
connections_at_min_replicas = 37 × 4   = 148
connections_at_max_replicas = 37 × 20  = 740
```

### Comparison to Postgres ceiling

The pool-sizing comment in `core/postgres_client.py:85` assumes
`max_connections = 100`. If that is the actual configured value of the
production Postgres cluster (TODO: confirm in `isA_Cloud` Helm values), the
gap is severe:

| Scenario                          | Connections needed | Postgres ceiling | Gap                 |
| --------------------------------- | ------------------ | ---------------- | ------------------- |
| 35 services × HPA min (2 pods)    | **140**            | 100              | **+40 over (40%)**  |
| 35 services × HPA max (10 pods)   | **700**            | 100              | **+600 over (7×)**  |
| 37 services × HPA min             | **148**            | 100              | **+48 over (48%)**  |
| 37 services × HPA max             | **740**            | 100              | **+640 over (7.4×)**|

### Implications

- **Already over budget at HPA min.** Today's static comment "35×2=70, under 100"
  is correct *only* if every service runs as a single pod. With `replicas: 2`
  default and HPA min=2, baseline demand for the **35 services currently
  deployed via Helm** is already 140 connections; adding the 2 not-yet-deployed
  services (`project_service`, `sharing_service`) pushes baseline to 148.
- **HPA scale-out will exhaust the pool long before reaching `maxReplicas`.**
  Newly scheduled pods will fail to acquire connections; expect
  `connection refused` / `too many clients already` errors during traffic
  spikes.
- **Migrations + service pods compete for the same budget.** The pre-deploy
  migration job ([#349](https://github.com/xenoISA/isA_user/issues/349))
  opens its own connections during rollout.
- **Multi-tenant SaaS clusters often run `max_connections = 200–500`.**
  Confirm the actual ceiling before drawing conclusions, but even at 500
  the HPA-max scenario (700) is over budget.

### Action items (out of scope for this doc — see [#346](https://github.com/xenoISA/isA_user/issues/346))

- [ ] Confirm `max_connections` on the production Postgres instance.
- [ ] Adopt PgBouncer (transaction pooling) in front of Postgres so each pod
      reuses a small set of upstream connections.
- [ ] Tier-aware pool sizing: Tier 1 services may justify larger pools than
      Tier 4 batch / cron-style services.
- [ ] Consider lowering `HPA.maxReplicas` for low-traffic Tier 4 services.

## Redis Connection Budget

Redis is used by a subset of services for caching, sessions, and rate-limit
state. Issue [#347](https://github.com/xenoISA/isA_user/issues/347) introduced
broader Redis usage; the pool sizing wrapper is not yet documented here.

### Known Redis users (from grep across `microservices/`)

`auth_service` (rate limiting), `session_service`, `storage_service`,
`payment_service`, `billing_service`, `weather_service`. **TODO: enumerate
authoritative list once #347 lands.**

### Math (assuming a default `redis-py` connection pool of `max_connections = 50`)

```
connections_per_pod   = 50  (redis-py default)
redis_users_estimate  = ~10 services (out of 37)

at HPA min (2 pods/service): 10 × 2 × 50  = 1,000 connection slots reserved
at HPA max (10 pods):        10 × 10 × 50 = 5,000 connection slots reserved
```

> **TODO**: These are pool *capacities*, not active connections. Redis with
> `maxclients = 10000` (default) accommodates this on paper, but bursty
> behavior and pipelining can spike actual concurrency. Validate with
> `INFO clients` during load tests.

### Action items

- [ ] Document the per-service Redis pool size knob (likely `REDIS_MAX_CONNECTIONS`).
- [ ] Confirm production Redis `maxclients`.
- [ ] Add a pooling layer if multiple services share a single Redis instance
      and aggregate pool capacity is too large.

## Memory Budget at Full Scale

```
memory_request_per_pod = 512Mi
memory_limit_per_pod   = 1Gi   (1024Mi)

services × pods × request:
  35 services × HPA min (2 pods) × 512Mi = 35 × 1,024Mi  = ~35 GiB requested
  35 services × HPA max (10 pods) × 512Mi = 35 × 5,120Mi = ~175 GiB requested

services × pods × limit (worst-case burst):
  35 services × HPA min × 1Gi  = 70 GiB
  35 services × HPA max × 1Gi  = 350 GiB
```

| Scenario                              | Total memory requests | Total memory limits |
| ------------------------------------- | --------------------- | ------------------- |
| 35 × HPA min (2 pods)                 | 35 GiB                | 70 GiB              |
| 35 × HPA max (10 pods)                | **175 GiB**           | **350 GiB**         |
| 37 × HPA max (10 pods)                | 185 GiB               | 370 GiB             |

### Implications

- A baseline cluster needs **~35 GiB** allocatable just for `isA_user` pods at
  HPA-min. Add headroom for system pods, DaemonSets, and the
  `isA_Cloud`/`isA_Model` workloads sharing the cluster.
- Hitting HPA-max across all services simultaneously requires **175 GiB** of
  memory requests — likely exceeds a small staging cluster.
- The `memoryUtilization` HPA target is `80%`; if RSS climbs to 80% of 512Mi
  request (≈410Mi), HPA scales out. p95 RSS measurements are needed
  per-service to know whether the 512Mi request is realistic or wasteful.

### TODO

- [ ] Measure p95 RSS per service in staging under typical load.
- [ ] Right-size `requests.memory` per tier once data exists.

## NATS Subscription Budget

NATS JetStream is used pervasively — **34+ of 37 services** import or use
`nats`/`jetstream` (verified by `grep -rln "nats\|JetStream" microservices/`).
The set of services with explicit subscribers (vs. publish-only) currently
covers most of the same set.

### Estimated durable consumer count

- Each service that subscribes typically declares ≥1 durable consumer per
  event subject it cares about. Subjects observed include `wallet.events.*`,
  `auth.role-events.*`, `billing.usage.*`, etc.
- Conservative estimate: **~3 durable consumers per subscribing service**.

```
subscribing_services    ≈ 34
consumers_per_service   ≈ 3
total_durable_consumers ≈ 100
```

### Implications

- NATS JetStream handles many thousands of consumers in practice; 100 is
  comfortably within reach for any reasonably sized JS deployment.
- Consumer count does **not** scale with pod count (durable consumers are
  shared across pods of the same service via queue-group semantics) — so
  HPA does not multiply NATS load the way it does for Postgres pools.
- The real risk is **slow consumers**: an HPA-scaled service with too few
  pods to keep up with stream throughput will accumulate pending messages.

### TODO

- [ ] Enumerate the actual durable consumer count from `nats stream consumer ls`
      in staging.
- [ ] Document per-stream `MaxAckPending` / `MaxDeliver` limits.

## Untiered / Missing-from-Helm services

| Service           | On disk | In `ports.yaml` | In `local-dev.sh` tier | In `values-production.yaml` |
| ----------------- | ------- | --------------- | ---------------------- | ---------------------------- |
| `sharing_service` | yes     | yes (8255)      | **no**                 | **no**                       |
| `project_service` | yes     | **no**          | **no**                 | **no**                       |

- `sharing_service` is in `config/ports.yaml` but still needs a tier assignment
  in `deployment/local-dev.sh` and an entry in
  `deployment/helm/values-production.yaml`.
- `project_service` is the more orphaned of the two: it exists as a
  microservice directory (with port `8260` hard-coded in
  `microservices/project_service/main.py:3,64`) but is missing from
  `config/ports.yaml`, all `TIER*_SERVICES` lists in `deployment/local-dev.sh`,
  and `deployment/helm/values-production.yaml`. It needs to be registered in
  all three (likely Tier 2 based on its dependencies).

Both are follow-ups on top of this doc.

## Outstanding TODOs (consolidated)

- [ ] Confirm production Postgres `max_connections` ceiling.
- [ ] Adopt PgBouncer or per-tier pool sizing ([#346](https://github.com/xenoISA/isA_user/issues/346)).
- [ ] Document Redis pool sizing knob and confirm `maxclients`.
- [ ] Measure p95 memory per service in staging; right-size `requests.memory`.
- [ ] Decide per-service `HPA.maxReplicas` — uniform `10` is unlikely to be
      the right ceiling for both auth_service and inventory_service.
- [ ] Register `project_service` in the inventory: add it to
      `config/ports.yaml`, assign it a tier in `deployment/local-dev.sh`
      (probably Tier 2 based on its dependencies), and add it to
      `deployment/helm/values-production.yaml`.
- [ ] Triage `sharing_service`: it is already in `config/ports.yaml` but
      still needs a tier in `deployment/local-dev.sh` and an entry in
      `deployment/helm/values-production.yaml`.
- [ ] Enumerate actual durable NATS consumer count and per-stream ack limits.
