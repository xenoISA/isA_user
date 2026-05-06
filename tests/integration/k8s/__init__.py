"""K8s scale-up integration tests (epic #345, story #354).

Exercises the HPA scale-up / scale-down path against a representative
service deployed into a kind cluster. Validates:

* Per-pod Postgres pool size honors :func:`core.postgres_client.compute_pool_size`
* All replicas pass ``/health`` during and after a scale event
* No 5xx / dropped requests while replicas churn
* Graceful drain (:mod:`core.graceful_shutdown`) keeps in-flight work alive

These tests are heavyweight (kind cluster spin-up ~60-90s) and are NOT
exercised in the standard pytest run. They are gated behind a path filter
in ``.github/workflows/ci.yml`` and an explicit ``workflow_dispatch``
trigger, plus the ``k8s`` pytest marker.
"""
