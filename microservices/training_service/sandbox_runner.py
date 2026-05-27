"""Constrained sandbox execution for first-party training exercises."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Any
from pathlib import Path

DENIED_CALLS = {"eval", "exec", "compile", "open", "__import__", "input"}
DENIED_IMPORTS = {
    "os",
    "pathlib",
    "shutil",
    "socket",
    "subprocess",
    "sys",
}


@dataclass(frozen=True)
class SandboxRunResult:
    executed: bool
    passed: bool
    output: str
    errors: list[str]
    durationMs: int


def run_agent_artifact(
    artifact: str,
    timeout_seconds: int,
    event: dict[str, Any] | None = None,
) -> SandboxRunResult:
    """Run a narrow Python handler artifact in a subprocess.

    This is not a replacement for the production container sandbox, but it gives
    Phase-1 exercises an auditable execution path while denying obvious host I/O.
    """
    errors = _validate_artifact(artifact)
    if errors:
        return SandboxRunResult(
            executed=False,
            passed=False,
            output="",
            errors=errors,
            durationMs=0,
        )

    with tempfile.TemporaryDirectory(prefix="isa-training-sbx-") as tmp:
        script = Path(tmp) / "runner.py"
        script.write_text(_runner_source(artifact, event), encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-S", str(script)],
                cwd=tmp,
                text=True,
                capture_output=True,
                timeout=max(1, min(timeout_seconds, 10)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return SandboxRunResult(
                executed=True,
                passed=False,
                output="",
                errors=["Execution timed out."],
                durationMs=timeout_seconds * 1000,
            )

    output = completed.stdout.strip()
    stderr = completed.stderr.strip()
    errors = [stderr] if stderr else []
    return SandboxRunResult(
        executed=True,
        passed=completed.returncode == 0,
        output=output,
        errors=errors,
        durationMs=0,
    )


def _validate_artifact(artifact: str) -> list[str]:
    try:
        tree = ast.parse(artifact)
    except SyntaxError as exc:
        return [f"Syntax error: {exc.msg}"]

    errors: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                root_name = alias.name.split(".")[0]
                if root_name in DENIED_IMPORTS:
                    errors.append(
                        f"Import not allowed in training sandbox: {root_name}"
                    )
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name in DENIED_CALLS:
                errors.append(f"Call not allowed in training sandbox: {name}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            errors.append("Dunder attribute access is not allowed in training sandbox.")

    return errors


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _runner_source(artifact: str, event: dict[str, Any] | None) -> str:
    encoded = json.dumps(artifact)
    encoded_event = json.dumps(event or {"input": "hello", "source": "isa_training"})
    return f"""
import json

artifact = {encoded}
event = {encoded_event}
safe_builtins = {{
    "abs": abs,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "round": round,
    "set": set,
    "str": str,
    "sum": sum,
    "tuple": tuple,
}}
namespace = {{}}
exec(artifact, {{"__builtins__": safe_builtins}}, namespace)
handler = namespace.get("handler")
if callable(handler):
    result = handler(event)
else:
    result = namespace.get("RESULT", "executed")
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
""".strip()
