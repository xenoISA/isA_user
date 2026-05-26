"""Adapter for isA_Agent_SDK-style sandbox lab tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .sandbox_runner import SandboxRunResult, run_agent_artifact

AGENT_SDK_TASK_TYPES = {"isa_agent_sdk_task", "isA_Agent_SDK_task", "agent_sdk_task"}


@dataclass(frozen=True)
class RubricFeedback:
    id: str
    passed: bool
    pointsAwarded: int
    pointsAvailable: int
    feedback: str


@dataclass(frozen=True)
class LabAdapterResult:
    executed: bool
    passed: bool
    score: int
    feedback: str
    executionLog: list[str]
    resourceUsage: dict[str, int | str]
    artifacts: list[dict[str, str]]
    rubricFeedback: list[RubricFeedback] = field(default_factory=list)
    proofEligible: bool = False
    adapter: str = "isA_Agent_SDK"


Runner = Callable[[str, int, dict[str, Any] | None], SandboxRunResult]


def is_agent_sdk_lab_task(task: Any) -> bool:
    if not isinstance(task, dict):
        return False
    task_type = task.get("type") or task.get("kind")
    if task_type in AGENT_SDK_TASK_TYPES:
        return True
    return task.get("sdk") == "isA_Agent_SDK" and isinstance(task.get("run"), dict)


def run_agent_sdk_lab_task(
    task: dict[str, Any],
    artifact: str,
    timeout_seconds: int,
    runner: Runner | None = None,
) -> LabAdapterResult:
    selected_runner = runner or run_agent_artifact
    run_config = task.get("run") if isinstance(task.get("run"), dict) else {}
    evaluation = (
        task.get("evaluation") if isinstance(task.get("evaluation"), dict) else {}
    )
    setup_steps = task.get("setup") if isinstance(task.get("setup"), list) else []
    run_input = (
        run_config.get("input") if isinstance(run_config.get("input"), dict) else None
    )
    entrypoint = str(run_config.get("entrypoint") or "handler")

    run_result = selected_runner(artifact, timeout_seconds, run_input)
    execution_log = [
        *[_setup_log(step) for step in setup_steps],
        f"run:{entrypoint}",
        *[line for line in [run_result.output, *run_result.errors] if line],
    ]
    artifacts = []
    if run_result.output:
        artifacts.append(
            {
                "kind": "agent_task_output",
                "name": "agent-output.json",
                "content": run_result.output,
            }
        )

    rubric_feedback = _score_rubric(evaluation.get("rubric"), run_result)
    score = _score_percent(rubric_feedback, run_result)
    passing_score = _int_value(evaluation.get("passingScore"), default=60)
    passed = run_result.executed and run_result.passed and score >= passing_score
    proof_eligible = bool(evaluation.get("proofEligible")) and passed
    feedback = (
        "isA_Agent_SDK lab task executed through the constrained local adapter."
        if passed
        else "isA_Agent_SDK lab task did not satisfy the configured evaluation contract."
    )

    return LabAdapterResult(
        executed=run_result.executed,
        passed=passed,
        score=score,
        feedback=feedback,
        executionLog=execution_log,
        resourceUsage={"durationMs": run_result.durationMs, "adapter": "local"},
        artifacts=artifacts,
        rubricFeedback=rubric_feedback,
        proofEligible=proof_eligible,
    )


def _setup_log(step: Any) -> str:
    if isinstance(step, dict):
        name = step.get("name") or step.get("uses") or "step"
        return f"setup:{name}"
    return f"setup:{step}"


def _score_rubric(rubric: Any, run_result: SandboxRunResult) -> list[RubricFeedback]:
    if not isinstance(rubric, list) or not rubric:
        return []

    feedback: list[RubricFeedback] = []
    output = run_result.output.lower()
    for index, item in enumerate(rubric, start=1):
        if not isinstance(item, dict):
            continue
        points_available = max(0, _int_value(item.get("points"), default=0))
        required = item.get("requiresOutputContains")
        matched = run_result.executed and run_result.passed
        if isinstance(required, str) and required:
            matched = matched and required.lower() in output
        feedback.append(
            RubricFeedback(
                id=str(item.get("id") or f"rubric_{index}"),
                passed=matched,
                pointsAwarded=points_available if matched else 0,
                pointsAvailable=points_available,
                feedback=(
                    "Matched required output signal."
                    if matched
                    else "Required output signal was not found."
                ),
            )
        )
    return feedback


def _score_percent(
    rubric_feedback: list[RubricFeedback], run_result: SandboxRunResult
) -> int:
    if not run_result.executed:
        return 0
    if not run_result.passed:
        return 40
    total = sum(item.pointsAvailable for item in rubric_feedback)
    if total <= 0:
        return 70
    awarded = sum(item.pointsAwarded for item in rubric_feedback)
    return round((awarded / total) * 100)


def _int_value(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default
