#!/usr/bin/env python3
"""Read-only audit for legacy Neo4j memory graph data before Falkor backfill.

This intentionally does not write to Neo4j or FalkorDB. Issue #395 requires
confirming data existence first; a migration/backfill is only justified when
this audit finds legacy graph rows.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Sequence


DEFAULT_MEMORY_LABELS = (
    "Memory",
    "MemoryEntity",
    "FactualMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "ProceduralMemory",
    "WorkingMemory",
    "SessionMemory",
)


@dataclass(frozen=True)
class AuditResult:
    namespace: str
    pod: str
    database: str
    total_nodes: int
    memory_nodes: int
    relationship_count: int
    backfill_required: bool
    checked_at: str


def _run(command: Sequence[str], *, timeout: int) -> str:
    completed = subprocess.run(
        list(command),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    return completed.stdout


def _parse_first_int(output: str) -> int:
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.lower() in {"count", "nodes", "relationships"}:
            continue
        try:
            return int(line)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse integer from cypher-shell output: {output!r}")


def cypher_count(
    *,
    namespace: str,
    pod: str,
    user: str,
    password: str,
    database: str,
    cypher: str,
    timeout: int,
) -> int:
    command = [
        "kubectl",
        "exec",
        "-n",
        namespace,
        pod,
        "--",
        "cypher-shell",
        "-u",
        user,
        "-p",
        password,
        "-d",
        database,
        cypher,
    ]
    return _parse_first_int(_run(command, timeout=timeout))


def build_memory_label_query(labels: Sequence[str]) -> str:
    label_predicate = " OR ".join(f"n:{label}" for label in labels)
    return f"MATCH (n) WHERE {label_predicate} RETURN count(n) AS count"


def audit(args: argparse.Namespace) -> AuditResult:
    total_nodes = cypher_count(
        namespace=args.namespace,
        pod=args.pod,
        user=args.user,
        password=args.password,
        database=args.database,
        cypher="MATCH (n) RETURN count(n) AS count",
        timeout=args.timeout,
    )
    memory_nodes = cypher_count(
        namespace=args.namespace,
        pod=args.pod,
        user=args.user,
        password=args.password,
        database=args.database,
        cypher=build_memory_label_query(args.memory_labels),
        timeout=args.timeout,
    )
    relationship_count = cypher_count(
        namespace=args.namespace,
        pod=args.pod,
        user=args.user,
        password=args.password,
        database=args.database,
        cypher="MATCH ()-[r]->() RETURN count(r) AS count",
        timeout=args.timeout,
    )
    return AuditResult(
        namespace=args.namespace,
        pod=args.pod,
        database=args.database,
        total_nodes=total_nodes,
        memory_nodes=memory_nodes,
        relationship_count=relationship_count,
        backfill_required=memory_nodes > 0,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit whether legacy Neo4j memory graph data needs FalkorDB backfill."
    )
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--pod", default="neo4j-0")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", required=True)
    parser.add_argument("--database", default="neo4j")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--memory-label",
        dest="memory_labels",
        action="append",
        default=[],
        help="Neo4j label to count as memory graph data; repeatable.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.memory_labels:
        args.memory_labels = list(DEFAULT_MEMORY_LABELS)
    result = audit(args)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 2 if result.backfill_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
