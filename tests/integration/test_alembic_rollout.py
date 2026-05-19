"""L3 Integration tests for the Alembic rollout across services.

Closes the #463 deferred follow-up: extends the Alembic adoption from
project_service (PR #467) to memory_service, artifact_service, and
project_sharing_service.

Per service we verify:
  1. The shared `alembic/env.py` resolves the service's version path
     via `ScriptDirectory.from_config` — i.e. the fix landed in PR #467
     (rebuilding the bound ScriptDirectory in place) still works once
     new services are added to the registry.
  2. The revision chain is intact — there are no orphaned
     `down_revision` references, exactly one head, and exactly one
     root, and the chain length matches the number of revision files.

This file also pins the project_service head and asserts the
``proj_005`` revision content — item #5 of the xenoISA/isA_#452 epic
(backfill + declarative NOT NULL on ``projects.owner_id``).

These are pure file/config tests — no database required — so they can
run on the same CI lane as the existing L1/L2 Alembic suites.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from core.migration_helpers import (
    get_service_version_path,
    get_version_table,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Services covered by this rollout batch.  project_service is omitted —
# it has its own dedicated suite under tests/integration/project_service/
# and was the original adoption in PR #467.
ROLLOUT_SERVICES = (
    "memory_service",
    "artifact_service",
    "project_sharing_service",
    "connector_service",
)

# Expected HEAD per service. Kept here (rather than read from disk) so
# the test fails loudly if anyone adds/removes revisions without thinking
# about the chain.
EXPECTED_HEAD = {
    "memory_service": "mem_011",
    "artifact_service": "art_004",
    "project_sharing_service": "psharing_001",
    "connector_service": "conn_001",
}

# Head expected for project_service after the proj_005 follow-up
# (defensive backfill + declarative NOT NULL). Pinned separately
# because project_service is not part of the ROLLOUT_SERVICES batch
# above (it was the original adoption).
PROJECT_SERVICE_HEAD = "proj_005"


def _script_for(service: str) -> ScriptDirectory:
    """Build a ScriptDirectory the same way env.py does at CLI time."""
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("version_locations", str(get_service_version_path(service)))
    return ScriptDirectory.from_config(cfg)


# ---------------------------------------------------------------------------
# Discovery — env.py must find the service's revisions.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", ROLLOUT_SERVICES)
def test_env_discovers_service_revisions(service: str) -> None:
    """env.py's ScriptDirectory rebuild must locate the service's revisions.

    Mirrors the post-#467 fix: setting `version_locations` is not enough
    because the CLI binds ScriptDirectory before env.py runs, so the
    real check is whether `ScriptDirectory.from_config` actually picks
    up our per-service path.
    """
    script = _script_for(service)
    heads = script.get_heads()
    assert len(heads) == 1, (
        f"{service} must have exactly one head, got {heads!r}. "
        "Multiple heads usually mean a forked down_revision chain."
    )
    assert heads[0] == EXPECTED_HEAD[service], (
        f"{service} head drift: env.py resolved {heads[0]!r}, expected "
        f"{EXPECTED_HEAD[service]!r}. If you intentionally added a new "
        "revision, update EXPECTED_HEAD in this test."
    )


@pytest.mark.parametrize("service", ROLLOUT_SERVICES)
def test_version_table_name_is_per_service(service: str) -> None:
    """Each service must isolate its migration state in its own table.

    The shared env.py uses `alembic_version_<service>` (via
    get_version_table) so two services running upgrades against the same
    database don't stomp on each other.  Drift here means env.py would
    write into the wrong table and the smoke test ('SELECT version_num
    FROM alembic_version_<service>') would never find the row.
    """
    table = get_version_table(service)
    assert (
        table == f"alembic_version_{service}"
    ), f"version table for {service} must be 'alembic_version_{service}', got {table!r}"
    # Sanity: per-service tables never collide with the default.
    assert table != "alembic_version"


# ---------------------------------------------------------------------------
# Chain integrity — no orphaned down_revisions, correct length.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("service", ROLLOUT_SERVICES)
def test_revision_chain_is_intact(service: str) -> None:
    """Walk the chain — every down_revision must resolve to a real revision.

    Catches:
      - typos in down_revision strings (e.g. 'mem_010' → 'mem_10')
      - skipped revisions in the middle (orphan path)
      - more than one root (down_revision=None) — a forked history would
        silently produce a multi-head, which we'd already catch above,
        but this is a clearer signal.
    """
    script = _script_for(service)
    revs = list(script.walk_revisions())
    rev_ids = {r.revision for r in revs}

    roots = [r for r in revs if r.down_revision is None]
    assert len(roots) == 1, (
        f"{service} should have exactly one root revision "
        f"(down_revision=None), found {len(roots)}: "
        f"{[r.revision for r in roots]!r}"
    )

    for rev in revs:
        if rev.down_revision is None:
            continue
        # down_revision can be a string or tuple-of-strings; normalise.
        parents = (
            rev.down_revision
            if isinstance(rev.down_revision, tuple)
            else (rev.down_revision,)
        )
        for parent in parents:
            assert parent in rev_ids, (
                f"{service} revision {rev.revision} references missing "
                f"down_revision {parent!r}. Either the parent file was "
                "deleted or the revision id was typoed."
            )


@pytest.mark.parametrize("service", ROLLOUT_SERVICES)
def test_revision_file_count_matches_chain(service: str) -> None:
    """The number of *.py files on disk must equal the chain length.

    A mismatch usually means someone added a revision file but didn't
    wire it into `down_revision`, leaving a stranded revision that
    `alembic upgrade head` would never apply.
    """
    versions_dir = get_service_version_path(service)
    py_files = [p for p in versions_dir.glob("*.py") if not p.name.startswith("__")]

    script = _script_for(service)
    chain = list(script.walk_revisions())

    assert len(chain) == len(py_files), (
        f"{service}: {len(py_files)} revision .py files on disk but "
        f"{len(chain)} revisions in the alembic chain. Likely a "
        "stranded file that's not referenced by any down_revision."
    )


# ---------------------------------------------------------------------------
# project_service — proj_005: backfill + declarative NOT NULL on owner_id.
# (Item #5 of xenoISA/isA_#452 — follow-up to PR #467's proj_004 backfill.)
# ---------------------------------------------------------------------------


def test_project_service_head_is_proj_005() -> None:
    """project_service head must be ``proj_005`` after the owner_id follow-up.

    Pins the head so anyone adding a future revision has to update this
    test consciously — the same protection ROLLOUT_SERVICES gets via
    EXPECTED_HEAD.
    """
    script = _script_for("project_service")
    heads = script.get_heads()
    assert len(heads) == 1, (
        f"project_service must have exactly one head, got {heads!r}. "
        "Multiple heads usually mean a forked down_revision chain."
    )
    assert heads[0] == PROJECT_SERVICE_HEAD, (
        f"project_service head drift: env.py resolved {heads[0]!r}, "
        f"expected {PROJECT_SERVICE_HEAD!r}. If you intentionally added "
        "a new revision, update PROJECT_SERVICE_HEAD in this test."
    )


def test_project_service_chain_is_intact() -> None:
    """project_service revision chain must be unbroken through proj_005."""
    script = _script_for("project_service")
    revs = list(script.walk_revisions())
    rev_ids = {r.revision for r in revs}

    roots = [r for r in revs if r.down_revision is None]
    assert (
        len(roots) == 1
    ), f"project_service should have exactly one root revision, found {len(roots)}: {[r.revision for r in roots]!r}"

    for rev in revs:
        if rev.down_revision is None:
            continue
        parents = (
            rev.down_revision
            if isinstance(rev.down_revision, tuple)
            else (rev.down_revision,)
        )
        for parent in parents:
            assert (
                parent in rev_ids
            ), f"project_service revision {rev.revision} references missing down_revision {parent!r}."


def test_project_service_revision_file_count_matches_chain() -> None:
    """Disk file count for project_service must equal chain length."""
    versions_dir = get_service_version_path("project_service")
    py_files = [p for p in versions_dir.glob("*.py") if not p.name.startswith("__")]

    script = _script_for("project_service")
    chain = list(script.walk_revisions())

    assert len(chain) == len(
        py_files
    ), f"project_service: {len(py_files)} revision .py files on disk but {len(chain)} revisions in the alembic chain."


def test_proj_005_backfills_owner_id_from_user_id() -> None:
    """proj_005 must defensively backfill owner_id from user_id.

    The backfill must be idempotent (WHERE owner_id is empty/NULL only)
    and use ``user_id`` as the source — matching the proj_004 strategy
    documented in PR #467 and the project_repository.create_project
    ``effective_owner = owner_id or user_id`` invariant.
    """
    rev_file = (
        get_service_version_path("project_service") / "005_assert_owner_id_not_null.py"
    )
    assert rev_file.exists(), (
        "proj_005 revision file must exist at "
        "microservices/project_service/alembic/versions/005_assert_owner_id_not_null.py"
    )
    content = rev_file.read_text()

    # Backfill — copies user_id into owner_id, only where it's empty/NULL.
    assert (
        "UPDATE project.projects" in content
    ), "proj_005 must run a defensive UPDATE on project.projects."
    assert "user_id" in content, "proj_005 backfill must derive owner_id from user_id."
    # Idempotency guard — the WHERE clause must restrict to empty/NULL rows
    # so re-runs are no-ops on healthy databases.
    assert (
        "owner_id = ''" in content and "owner_id IS NULL" in content
    ), "proj_005 must guard the UPDATE with `WHERE owner_id = '' OR owner_id IS NULL` for idempotency."


def test_proj_005_declares_not_null_via_alter_column() -> None:
    """proj_005 must enforce NOT NULL declaratively via op.alter_column.

    The DB-level NOT NULL has been in place since proj_003 (via
    ``TEXT NOT NULL DEFAULT ''``), but stating it via ``op.alter_column``
    makes the invariant visible in the migration registry. A future
    alembic autogenerate run will not propose to drop it.
    """
    rev_file = (
        get_service_version_path("project_service") / "005_assert_owner_id_not_null.py"
    )
    content = rev_file.read_text()

    assert (
        "op.alter_column(" in content
    ), "proj_005 must call op.alter_column to declare the constraint."
    assert (
        '"owner_id"' in content or "'owner_id'" in content
    ), "proj_005 alter_column must target the owner_id column."
    assert (
        "nullable=False" in content
    ), "proj_005 must declare nullable=False on owner_id."
    assert (
        'schema="project"' in content or "schema='project'" in content
    ), "proj_005 alter_column must target the `project` schema explicitly — the public schema does not own this table."


def test_proj_005_downgrade_is_documented_noop() -> None:
    """proj_005's downgrade must be intentionally empty.

    The backfill is not reversible (no signal to distinguish backfilled
    rows from explicitly-set ones), and the NOT NULL constraint pre-
    dates this revision — dropping it would weaken the schema below the
    post-proj_003 baseline. A bare ``pass`` with a comment is the
    correct shape.
    """
    rev_file = (
        get_service_version_path("project_service") / "005_assert_owner_id_not_null.py"
    )
    content = rev_file.read_text()

    # Locate the downgrade body.
    assert "def downgrade()" in content
    downgrade_body = content.split("def downgrade()", 1)[1]
    # Must not reverse the backfill or drop NOT NULL.
    assert "DROP NOT NULL" not in downgrade_body.upper(), (
        "proj_005 downgrade must NOT drop the NOT NULL constraint — "
        "that would weaken the schema below the post-proj_003 baseline."
    )
    assert "UPDATE" not in downgrade_body.upper(), (
        "proj_005 downgrade must NOT attempt to reverse the backfill — "
        "there is no signal to distinguish backfilled rows."
    )
    # And must explicitly contain a `pass` (or be visibly inert).
    assert (
        "    pass" in downgrade_body
    ), "proj_005 downgrade should be a documented `pass` no-op."


# ---------------------------------------------------------------------------
# connector_service — conn_001 (xenoISA/isA_#464 backend slice).
#
# Four extra cases that pin the shape of the new service's first
# revision, mirroring the protections the ROLLOUT_SERVICES + project_service
# blocks above give the existing chains.
# ---------------------------------------------------------------------------


def test_connector_service_head_is_conn_001() -> None:
    """connector_service head must be ``conn_001`` after the #464 backend slice."""
    script = _script_for("connector_service")
    heads = script.get_heads()
    assert (
        len(heads) == 1
    ), f"connector_service must have exactly one head, got {heads!r}."
    assert heads[0] == "conn_001", (
        f"connector_service head drift: env.py resolved {heads[0]!r}, "
        "expected 'conn_001'. Update this test if a new revision was added intentionally."
    )


def test_conn_001_creates_connector_schema_and_tables() -> None:
    """conn_001 must create the ``connector`` schema plus both tables."""
    rev_file = (
        get_service_version_path("connector_service")
        / "conn_001_create_connector_tables.py"
    )
    assert rev_file.exists(), (
        "conn_001 revision file must exist at "
        "microservices/connector_service/alembic/versions/conn_001_create_connector_tables.py"
    )
    content = rev_file.read_text()

    assert (
        "CREATE SCHEMA IF NOT EXISTS connector" in content
    ), "conn_001 must create the `connector` schema idempotently."
    assert (
        "CREATE TABLE IF NOT EXISTS connector.connector" in content
    ), "conn_001 must create the per-user `connector.connector` install-state table."
    assert (
        "CREATE TABLE IF NOT EXISTS connector.custom_mcp_connector" in content
    ), "conn_001 must create the `connector.custom_mcp_connector` table."


def test_conn_001_enforces_unique_constraints() -> None:
    """conn_001 must constrain duplicate (user, connector_id) and (user, url)."""
    rev_file = (
        get_service_version_path("connector_service")
        / "conn_001_create_connector_tables.py"
    )
    content = rev_file.read_text()
    assert (
        "uq_connector_user_connector" in content
    ), "conn_001 must add UNIQUE(user_id, connector_id) on connector.connector."
    assert "uq_custom_mcp_user_url" in content, (
        "conn_001 must add UNIQUE(user_id, url) on connector.custom_mcp_connector — "
        "this is the idempotency guard for POST /connectors/custom."
    )


def test_conn_001_constrains_status_and_auth_kind() -> None:
    """conn_001 must CHECK status + auth_kind values so the API and DB agree."""
    rev_file = (
        get_service_version_path("connector_service")
        / "conn_001_create_connector_tables.py"
    )
    content = rev_file.read_text()
    # status enum on connector.connector
    assert "ck_connector_status" in content
    for v in ("connected", "pending_auth", "error", "disconnected"):
        assert v in content, f"conn_001 must allow status={v!r} on connector.connector."
    # auth_kind + status on custom_mcp_connector
    assert "ck_custom_mcp_auth_kind" in content
    for v in ("none", "pat", "oauth_oob"):
        assert (
            v in content
        ), f"conn_001 must allow auth_kind={v!r} on custom_mcp_connector."
    assert "ck_custom_mcp_status" in content
    for v in ("pending", "active", "error", "revoked"):
        assert (
            v in content
        ), f"conn_001 must allow status={v!r} on custom_mcp_connector."
