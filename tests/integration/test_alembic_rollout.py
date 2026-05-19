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
)

# Expected HEAD per service. Kept here (rather than read from disk) so
# the test fails loudly if anyone adds/removes revisions without thinking
# about the chain.
EXPECTED_HEAD = {
    "memory_service": "mem_011",
    "artifact_service": "art_004",
    "project_sharing_service": "psharing_001",
}


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
