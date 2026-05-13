from __future__ import annotations

import json
import subprocess

from scripts import audit_memory_graph_backfill as audit


def test_parse_first_int_skips_headers_and_warnings():
    output = """
WARNING: java native access warning
count
42
"""

    assert audit._parse_first_int(output) == 42


def test_build_memory_label_query_includes_all_labels():
    query = audit.build_memory_label_query(["Memory", "MemoryEntity"])

    assert query == (
        "MATCH (n) WHERE n:Memory OR n:MemoryEntity RETURN count(n) AS count"
    )


def test_main_outputs_no_backfill_when_no_memory_nodes(monkeypatch, capsys):
    counts = iter([5, 0, 9])

    def fake_count(**kwargs):
        return next(counts)

    monkeypatch.setattr(audit, "cypher_count", fake_count)

    exit_code = audit.main(
        [
            "--namespace",
            "isa-cloud-local",
            "--password",
            "secret",
        ]
    )

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert captured["total_nodes"] == 5
    assert captured["memory_nodes"] == 0
    assert captured["relationship_count"] == 9
    assert captured["backfill_required"] is False


def test_main_returns_two_when_memory_nodes_exist(monkeypatch, capsys):
    counts = iter([20, 3, 7])
    monkeypatch.setattr(audit, "cypher_count", lambda **kwargs: next(counts))

    exit_code = audit.main(
        [
            "--namespace",
            "isa-cloud-staging",
            "--password",
            "secret",
            "--memory-label",
            "Memory",
        ]
    )

    captured = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert captured["memory_nodes"] == 3
    assert captured["backfill_required"] is True


def test_cypher_count_invokes_kubectl_exec(monkeypatch):
    calls = []

    def fake_run(command, check, text, stdout, stderr, timeout):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="count\n4\n", stderr="")

    monkeypatch.setattr(audit.subprocess, "run", fake_run)

    result = audit.cypher_count(
        namespace="isa-cloud-local",
        pod="neo4j-0",
        user="neo4j",
        password="secret",
        database="neo4j",
        cypher="MATCH (n) RETURN count(n) AS count",
        timeout=10,
    )

    assert result == 4
    assert calls == [
        [
            "kubectl",
            "exec",
            "-n",
            "isa-cloud-local",
            "neo4j-0",
            "--",
            "cypher-shell",
            "-u",
            "neo4j",
            "-p",
            "secret",
            "-d",
            "neo4j",
            "MATCH (n) RETURN count(n) AS count",
        ]
    ]
