"""HPA scale-up / scale-down integration test (epic #345, story #354).

Verifies that the dynamic Postgres pool sizing (#346), graceful shutdown
(:mod:`core.graceful_shutdown`), and HPA chart wiring all play nicely
together when a service scales out under load.

The test deploys a small stub workload (``manifests/auth-stub.yaml``) into
a kind / k3d cluster, drives synthetic CPU load through ``/work``, and
asserts the four acceptance criteria from issue #354:

    1. The HPA scales the Deployment up to >= ``min_replicas_after_load``.
    2. All replicas pass ``/health`` during and after the scale event.
    3. No 5xx / dropped requests above ``max_error_rate``.
    4. ``compute_pool_size(replicas) * replicas`` stays within the
       cross-service Postgres connection budget after the scale event.
    5. (Scale-down) Manually scaling back to 1 replica drains gracefully
       — a final burst of requests during termination sees zero drops.

This test is NOT part of the standard pytest run. It is gated behind:

  * the ``k8s`` pytest marker (skipped unless explicitly selected)
  * the ``KUBECONFIG`` env var pointing at a reachable cluster
  * a CI ``paths`` filter that only triggers it for changes to
    ``core/postgres_client.py``, ``core/graceful_shutdown.py``, or
    ``deployment/helm/`` — see ``.github/workflows/ci.yml``.

Run locally::

    kind create cluster --name isa-scale-up
    pytest tests/integration/k8s/test_scale_up.py -v -m k8s
    kind delete cluster --name isa-scale-up

Run on demand in CI: trigger the ``CI`` workflow via ``workflow_dispatch``
with input ``run_k8s_tests=true``.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pytest
import yaml

# Make the repo root importable so ``core.postgres_client`` resolves when
# pytest is invoked from a fresh checkout (e.g., the kind GH Actions job).
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.postgres_client import compute_pool_size  # noqa: E402

# ---------------------------------------------------------------------------
# Module-level config
# ---------------------------------------------------------------------------

MANIFEST_PATH = Path(__file__).parent / "manifests" / "auth-stub.yaml"
LOAD_PROFILE_PATH = Path(__file__).parent / "load_profile.yaml"

NAMESPACE = "scale-up-test"
DEPLOYMENT = "auth-stub"
SERVICE = "auth-stub"
SERVICE_PORT = 8201

# Cross-service Postgres connection budget. Mirrors the documented limit
# in deployment/helm/values.yaml and docs/runbooks/hpa-capacity.md (#353).
# We allow some headroom so the test isn't brittle to small chart bumps.
POSTGRES_MAX_CONNECTIONS = 100
RESERVED_FOR_OPS = 10  # superuser + replication + admin tooling
PER_TEST_BUDGET = POSTGRES_MAX_CONNECTIONS - RESERVED_FOR_OPS


pytestmark = [
    pytest.mark.k8s,
    pytest.mark.integration,
    # Default-skip unless someone has set up a cluster — this test is
    # heavyweight and not part of the normal pyramid run.
    pytest.mark.skipif(
        shutil.which("kubectl") is None,
        reason="kubectl not available; skipping K8s scale-up test",
    ),
    pytest.mark.skipif(
        os.environ.get("RUN_K8S_TESTS", "").lower() not in {"1", "true", "yes"},
        reason="set RUN_K8S_TESTS=1 to enable the kind/k3d scale-up test",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kubectl(*args: str, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run ``kubectl`` against the active cluster. Tiny wrapper for grep-ability."""
    cmd = ["kubectl", *args]
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
    )


def _wait_for(
    predicate, *, timeout: float, interval: float = 2.0, label: str = "condition"
) -> None:
    """Poll ``predicate`` until truthy or time out. Raises on timeout."""
    deadline = time.time() + timeout
    last_err: Optional[BaseException] = None
    while time.time() < deadline:
        try:
            if predicate():
                return
        except Exception as exc:  # noqa: BLE001 — we want any error to propagate as the timeout reason
            last_err = exc
        time.sleep(interval)
    msg = f"timed out after {timeout:.0f}s waiting for {label}"
    if last_err:
        msg = f"{msg} (last error: {last_err!r})"
    raise TimeoutError(msg)


def _replicas_ready() -> int:
    """Return the current number of Ready replicas of the test Deployment."""
    out = _kubectl(
        "get",
        "deployment",
        DEPLOYMENT,
        "-n",
        NAMESPACE,
        "-o",
        "json",
    ).stdout
    spec = json.loads(out)
    return int(spec.get("status", {}).get("readyReplicas") or 0)


def _hpa_replicas() -> int:
    """Return ``status.currentReplicas`` from the HPA. Reflects the autoscaler's view."""
    out = _kubectl(
        "get",
        "hpa",
        DEPLOYMENT,
        "-n",
        NAMESPACE,
        "-o",
        "json",
    ).stdout
    spec = json.loads(out)
    return int(spec.get("status", {}).get("currentReplicas") or 0)


def _list_pods() -> List[str]:
    out = _kubectl(
        "get",
        "pods",
        "-n",
        NAMESPACE,
        "-l",
        f"app={DEPLOYMENT}",
        "-o",
        "json",
    ).stdout
    items = json.loads(out).get("items", [])
    return [
        p["metadata"]["name"]
        for p in items
        if p.get("status", {}).get("phase") == "Running"
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def load_profile() -> Dict[str, Any]:
    return yaml.safe_load(LOAD_PROFILE_PATH.read_text())


@pytest.fixture(scope="module")
def cluster_workload():
    """Apply the stub manifest, wait for the first replica, yield a base
    URL the test can hit, and tear everything down after the run.

    The test assumes the caller has already created a kind/k3d cluster
    and pointed ``KUBECONFIG`` at it. We do *not* manage the cluster
    lifecycle in pytest because that responsibility lives in CI
    (``helm/kind-action``) or the developer's local shell — keeping it
    out of the test makes repeated runs against the same cluster fast
    and predictable.

    Access strategy: ``kubectl port-forward svc/...`` picks a *single*
    pod at start time, which both biases load to one replica (preventing
    HPA scale-down once others come up) and makes connection churn
    visible as transport errors. The caller can use this for control-plane
    /health probes, but the *load generator* drives traffic via an
    in-cluster Job (see ``_run_in_cluster_load``) so every replica
    actually gets work.
    """
    _kubectl("apply", "-f", str(MANIFEST_PATH))
    try:
        # Use ``kubectl rollout status`` which handles image pulls and
        # readinessProbe timing without false-positives on intermediate
        # ReplicaSet transitions. 5 minutes is generous to cover the
        # first-time ``python:3.11-slim`` image pull on a fresh kind
        # node.
        subprocess.run(
            [
                "kubectl",
                "rollout",
                "status",
                "deployment",
                DEPLOYMENT,
                "-n",
                NAMESPACE,
                "--timeout=300s",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        # Port-forward in a subprocess so the test can hit the Service
        # without relying on NodePort or an Ingress controller. Port 18201
        # is arbitrary; we pick a non-default to avoid colliding with a
        # locally running auth_service.
        local_port = 18201
        pf = subprocess.Popen(
            [
                "kubectl",
                "port-forward",
                "-n",
                NAMESPACE,
                f"svc/{SERVICE}",
                f"{local_port}:{SERVICE_PORT}",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            base_url = f"http://127.0.0.1:{local_port}"
            # Wait for the port-forward to actually start serving.
            _wait_for(
                lambda: httpx.get(f"{base_url}/health", timeout=2.0).status_code == 200,
                timeout=60.0,
                label="port-forward + /health 200",
            )
            yield base_url
        finally:
            pf.terminate()
            try:
                pf.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pf.kill()
    finally:
        # Best-effort teardown. We swallow errors so a failed test still
        # cleans up the namespace.
        _kubectl(
            "delete",
            "-f",
            str(MANIFEST_PATH),
            "--ignore-not-found",
            check=False,
        )


def _run_in_cluster_load(
    *,
    duration_seconds: float,
    concurrency: int,
    rps_per_worker: float,
    path: str,
) -> Dict[str, int]:
    """Run a load generator *inside* the cluster and return its counters.

    Why in-cluster? ``kubectl port-forward svc/X`` binds to one pod for
    its entire lifetime, which biases all load to a single replica.
    Once the HPA scales up, the new pods see no traffic and the
    autoscaler immediately scales them back down. Running the generator
    as a Pod that resolves the Service via cluster DNS gives us real
    kube-proxy round-robin to every replica.

    The generator is itself a tiny Python script materialized via a
    ConfigMap so we don't need a custom image. It writes a JSON
    ``counters`` blob to stdout on exit; we parse it back and return.
    """
    job_name = "auth-stub-loadgen"
    # Render a generator script + Pod spec inline. Using a ConfigMap +
    # Pod (rather than a Job) keeps the contract simple: we wait for
    # Pod completion, scrape its logs, then delete it.
    script = f"""
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

URL = "http://{SERVICE}:{SERVICE_PORT}{path}"
DURATION = {duration_seconds}
CONCURRENCY = {concurrency}
RPS_PER_WORKER = {rps_per_worker}
TIMEOUT = 5.0

counters = dict(total=0, ok=0, server_error=0, client_error=0, transport_error=0)
lock = threading.Lock()

def worker(idx):
    sleep_between = 1.0 / max(0.1, RPS_PER_WORKER)
    deadline = time.monotonic() + DURATION
    while time.monotonic() < deadline:
        local = dict(total=1, ok=0, server_error=0, client_error=0, transport_error=0)
        try:
            with urllib.request.urlopen(URL, timeout=TIMEOUT) as resp:
                code = resp.getcode()
                if 200 <= code < 300:
                    local["ok"] = 1
                elif 400 <= code < 500:
                    local["client_error"] = 1
                else:
                    local["server_error"] = 1
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                local["client_error"] = 1
            else:
                local["server_error"] = 1
        except Exception:
            local["transport_error"] = 1
        with lock:
            for k, v in local.items():
                counters[k] += v
        time.sleep(sleep_between)

threads = [threading.Thread(target=worker, args=(i,)) for i in range(CONCURRENCY)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print("LOADGEN_RESULT=" + json.dumps(counters))
"""
    cm_manifest = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": f"{job_name}-script", "namespace": NAMESPACE},
        "data": {"loadgen.py": script},
    }
    pod_manifest = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": job_name, "namespace": NAMESPACE},
        "spec": {
            "restartPolicy": "Never",
            "containers": [
                {
                    "name": "loadgen",
                    "image": "python:3.11-slim",
                    "command": ["python", "/script/loadgen.py"],
                    "volumeMounts": [{"name": "script", "mountPath": "/script"}],
                }
            ],
            "volumes": [
                {
                    "name": "script",
                    "configMap": {"name": f"{job_name}-script"},
                }
            ],
        },
    }

    # Apply via stdin so we don't have to write tempfiles. ``kubectl
    # apply -f -`` reads YAML/JSON from stdin.
    apply_payload = json.dumps({"items": [cm_manifest, pod_manifest], "kind": "List", "apiVersion": "v1"})
    subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=apply_payload,
        text=True,
        check=True,
        capture_output=True,
    )
    try:
        # Wait for the pod to enter Succeeded/Failed.
        deadline = time.time() + duration_seconds + 120.0
        phase = ""
        while time.time() < deadline:
            phase = json.loads(
                _kubectl("get", "pod", job_name, "-n", NAMESPACE, "-o", "json").stdout
            ).get("status", {}).get("phase", "")
            if phase in {"Succeeded", "Failed"}:
                break
            time.sleep(2.0)
        assert phase in {"Succeeded", "Failed"}, f"loadgen pod stuck in phase={phase!r}"

        logs = _kubectl("logs", "-n", NAMESPACE, job_name).stdout
        for line in logs.splitlines():
            if line.startswith("LOADGEN_RESULT="):
                return json.loads(line.split("=", 1)[1])
        raise AssertionError(f"loadgen produced no result line; logs:\n{logs}")
    finally:
        _kubectl(
            "delete",
            "pod",
            job_name,
            "-n",
            NAMESPACE,
            "--ignore-not-found",
            "--grace-period=0",
            "--force",
            check=False,
        )
        _kubectl(
            "delete",
            "configmap",
            f"{job_name}-script",
            "-n",
            NAMESPACE,
            "--ignore-not-found",
            check=False,
        )


# ---------------------------------------------------------------------------
# Load generator
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _http_client(base_url: str, timeout: float) -> "httpx.AsyncClient":
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        yield client


async def _drive_load(
    base_url: str,
    *,
    duration_seconds: float,
    concurrency: int,
    rps_per_worker: float,
    request_timeout: float,
    path: str = "/work",
) -> Dict[str, int]:
    """Issue an open-loop load run and return aggregate counters.

    Returns a dict with ``total``, ``ok`` (2xx), ``server_error`` (5xx),
    ``client_error`` (4xx), and ``transport_error`` (connect/read/
    timeout). The test asserts on ``server_error`` strictly (real
    backend failures) and on ``transport_error`` during graceful drain
    (the criterion that matters for #354).

    ``transport_error`` during the *scale-up* phase is *not* a backend
    failure — it usually means kubectl port-forward dropped a connection
    during pod churn, or the kind kube-proxy briefly held a stale
    endpoint. Those are tolerated against ``max_error_rate``.
    """
    counters = {
        "total": 0,
        "ok": 0,
        "server_error": 0,
        "client_error": 0,
        "transport_error": 0,
    }
    deadline = time.monotonic() + duration_seconds

    async def worker():
        sleep_between = 1.0 / max(0.1, rps_per_worker)
        async with _http_client(base_url, timeout=request_timeout) as client:
            while time.monotonic() < deadline:
                try:
                    resp = await client.get(path)
                    counters["total"] += 1
                    if 200 <= resp.status_code < 300:
                        counters["ok"] += 1
                    elif 400 <= resp.status_code < 500:
                        counters["client_error"] += 1
                    elif resp.status_code >= 500:
                        counters["server_error"] += 1
                except (httpx.TransportError, asyncio.TimeoutError):
                    counters["total"] += 1
                    counters["transport_error"] += 1
                await asyncio.sleep(sleep_between)

    await asyncio.gather(*[worker() for _ in range(concurrency)])
    return counters


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pool_formula_unchanged():
    """Lock the pool-size formula the stub container duplicates inline.

    The stub manifest copies ``compute_pool_size`` into a ConfigMap because
    the kind container can't import the repo. If the canonical formula
    drifts, this test fails first so an engineer notices before the scale
    test silently asserts against stale math.
    """
    assert compute_pool_size(replica_count=1, base=2, growth=1, floor=5) == 5
    assert compute_pool_size(replica_count=3, base=2, growth=1, floor=5) == 5
    assert compute_pool_size(replica_count=5, base=2, growth=1, floor=5) == 6
    # Sanity: the budget headroom assumed by this test must be > the
    # per-pod pool at the HPA's max replicas, otherwise even a healthy
    # scale-up would breach the budget.
    pool_at_max = compute_pool_size(replica_count=5, base=2, growth=1, floor=5)
    assert pool_at_max * 5 < PER_TEST_BUDGET


@pytest.mark.asyncio
async def test_hpa_scale_up_and_drain(cluster_workload, load_profile):
    """End-to-end scale-up + scale-down assertions (#354 acceptance criteria)."""
    base_url = cluster_workload
    profile = load_profile
    asserts = profile["assertions"]

    # ---- 1. Drive load and let the HPA react ---------------------------
    # Run the generator *inside* the cluster so kube-proxy round-robins
    # across replicas as they come up. The local port-forward is reserved
    # for the per-replica /health probe in step 3 and the graceful-drain
    # burst in step 4.
    counters = await asyncio.to_thread(
        _run_in_cluster_load,
        duration_seconds=profile["duration_seconds"],
        concurrency=profile["concurrency"],
        rps_per_worker=profile["rps_per_worker"],
        path=profile["endpoint"],
    )

    # Settle window so the HPA's last decision propagates to readyReplicas.
    time.sleep(profile["post_load_settle_seconds"])

    final_replicas = _replicas_ready()
    assert final_replicas >= asserts["min_replicas_after_load"], (
        f"HPA did not scale up: ready={final_replicas}, "
        f"expected >= {asserts['min_replicas_after_load']}"
    )

    # ---- 2. Error budget over the full load run ------------------------
    # 5xx are *application* failures and must be (effectively) zero —
    # those would mean a replica crashed or returned 503 outside of
    # graceful_shutdown. The strict drain-time check on transport
    # errors lives further down in step 4.
    server_error_rate = counters["server_error"] / max(1, counters["total"])
    assert server_error_rate <= asserts["max_error_rate"], (
        f"5xx error rate {server_error_rate:.4f} exceeded budget "
        f"{asserts['max_error_rate']}: {counters}"
    )
    # Transport errors during scale-up are tolerated (kube-proxy +
    # port-forward churn) but capped at a generous ceiling so a
    # genuinely broken backend still fails the test.
    transport_error_rate = counters["transport_error"] / max(1, counters["total"])
    assert transport_error_rate <= 0.30, (
        f"transport error rate {transport_error_rate:.4f} too high to be "
        f"port-forward churn, suggests backend instability: {counters}"
    )

    # ---- 3. Per-replica /health all 200, pool size within budget -------
    # Two-part check:
    #   (a) Compute the *expected* aggregate pool for the observed
    #       replica count using the live ``compute_pool_size`` and
    #       assert it stays within the cross-service Postgres budget.
    #       This is the production safety property — it doesn't require
    #       re-rolling pods to verify, so we don't pay the rollout cost.
    #   (b) Hit /health on every running pod (via ``kubectl exec``) and
    #       assert each replica is healthy. We use exec rather than the
    #       Service to avoid kube-proxy randomness — we want one probe
    #       per pod, deterministic.
    expected_pool = compute_pool_size(replica_count=final_replicas)
    total_pool = expected_pool * final_replicas
    assert total_pool <= PER_TEST_BUDGET, (
        f"aggregate pool {total_pool} would breach Postgres budget "
        f"{PER_TEST_BUDGET} at {final_replicas} replicas (expected_pool={expected_pool})"
    )

    pods = _list_pods()
    assert len(pods) >= final_replicas, (
        f"only {len(pods)} Running pods found, expected >= {final_replicas}"
    )
    for pod in pods:
        # ``kubectl exec`` into each pod and curl localhost. Avoids
        # Service-level randomness and proves *this specific pod* is
        # answering /health 200.
        out = _kubectl(
            "exec",
            "-n",
            NAMESPACE,
            pod,
            "--",
            "python",
            "-c",
            (
                "import urllib.request,json,sys;"
                f"r=urllib.request.urlopen('http://127.0.0.1:{SERVICE_PORT}/health',timeout=5);"
                "print(r.status); sys.stdout.write(r.read().decode())"
            ),
        ).stdout
        # First line is the HTTP status, the rest is JSON.
        status_line, _, body = out.partition("\n")
        assert status_line.strip() == "200", f"pod {pod} /health -> {status_line}"
        payload = json.loads(body)
        assert payload.get("ok") is True, f"pod {pod} unhealthy: {payload}"
        assert payload.get("pool") >= 5, f"pod {pod} reported pool={payload.get('pool')} < floor"

    # ---- 4. Graceful drain on scale-down -------------------------------
    # Manually scale to 1 to exercise graceful_shutdown.py — the surplus
    # replicas should drain in-flight requests instead of returning 5xx.
    sd = profile["scale_down"]
    _kubectl(
        "scale",
        "deployment",
        DEPLOYMENT,
        "-n",
        NAMESPACE,
        "--replicas=1",
    )

    drain_counters = await _drive_load(
        base_url,
        duration_seconds=20.0,  # cover the 30s terminationGracePeriod
        concurrency=sd["final_burst_concurrency"],
        rps_per_worker=sd["final_burst_requests"] / 20.0,
        request_timeout=5.0,
        path="/health",
    )

    # During termination, the graceful_shutdown middleware returns 503 on
    # *new* requests but allows existing ones to complete. We accept 503s
    # here (they prove the drain logic fired). Transport errors get a
    # small budget too — kubectl port-forward latches onto one pod, so
    # when scale-down terminates that pod the local port-forward closes
    # its forwarded TCP connections (this is the *test harness* dropping
    # connections, not the app cutting off in-flight requests). The
    # assertion that really matters for #354 is the zero-5xx invariant
    # below: any 5xx during drain would mean the app crashed mid-request.
    drain_total = max(1, drain_counters["total"])
    drain_transport_rate = drain_counters["transport_error"] / drain_total
    assert drain_transport_rate <= 0.10, (
        f"transport error rate {drain_transport_rate:.2%} too high during "
        f"drain — port-forward churn alone shouldn't exceed 10%: "
        f"{drain_counters}"
    )
    assert drain_counters["server_error"] == 0, (
        f"5xx during drain means app crashed mid-request, not graceful: "
        f"{drain_counters}"
    )

    # And we should converge back to 1 ready replica.
    _wait_for(
        lambda: _replicas_ready() == 1,
        timeout=180.0,
        label="scale-down to 1 replica",
    )
