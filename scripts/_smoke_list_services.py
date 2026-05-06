#!/usr/bin/env python3
"""Emit (k8s_service_name, port) TSV pairs for every microservice in
config/ports.yaml. Used by .github/workflows/deploy.yml to fan out
`kubectl port-forward` invocations before running scripts/smoke_test.sh.

Output format (no header):
    <k8s_service>\t<port>
"""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    ports_file = repo_root / "config" / "ports.yaml"
    if not ports_file.is_file():
        print(f"ports.yaml not found: {ports_file}", file=sys.stderr)
        return 1

    try:
        import yaml  # type: ignore
    except ImportError:
        print("PyYAML required (pip install pyyaml)", file=sys.stderr)
        return 1

    data = yaml.safe_load(ports_file.read_text()) or {}
    services = data.get("microservices") or {}

    for name, cfg in services.items():
        if not isinstance(cfg, dict):
            continue
        port = cfg.get("port")
        if not isinstance(port, int):
            continue
        short = cfg.get("k8s_service") or name.replace("_service", "")
        print(f"{short}\t{port}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
