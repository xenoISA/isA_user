"""Audit-safe observability primitives for the training service."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Mapping


def request_id_from_headers(headers: Mapping[str, str]) -> str:
    """Use the gateway request id when present, otherwise create a local id."""
    incoming = headers.get("x-request-id") or headers.get("x-correlation-id")
    if incoming and incoming.strip():
        return incoming.strip()
    return f"training-{uuid.uuid4().hex}"


@dataclass
class TrainingObservability:
    """Small Prometheus-style recorder for the Phase-1 service.

    This intentionally avoids adding a metrics dependency while the deployment
    target is still evolving. The text format can be scraped by simple probes
    and replaced by the platform metrics client later.
    """

    _counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = field(
        default_factory=lambda: defaultdict(int),
    )
    _timings_ms: dict[tuple[str, tuple[tuple[str, str], ...]], list[int]] = field(
        default_factory=lambda: defaultdict(list),
    )

    def increment(self, name: str, **labels: str | int | bool | None) -> None:
        amount = int(labels.get("amount") or 1)
        key = (name, self._label_items(labels))
        self._counters[key] += amount

    def observe_ms(
        self, name: str, value_ms: int, **labels: str | int | bool | None
    ) -> None:
        key = (name, self._label_items(labels))
        self._timings_ms[key].append(max(0, value_ms))

    def record_http_request(
        self, method: str, status_code: int, duration_ms: int
    ) -> None:
        labels = {"method": method.upper(), "status": str(status_code)}
        self.increment("isa_training_http_requests_total", **labels)
        self.observe_ms("isa_training_http_request_duration_ms", duration_ms, **labels)

    def record_assistant_response(self, status: str, citation_count: int) -> None:
        self.increment("isa_training_assistant_requests_total", status=status)
        self.increment(
            "isa_training_assistant_citations_total", amount=max(0, citation_count)
        )

    def record_sandbox_evaluation(self, executed: bool, passed: bool) -> None:
        self.increment(
            "isa_training_sandbox_evaluations_total",
            executed=executed,
            passed=passed,
        )

    def record_completion_proof_verification(self, status: str) -> None:
        self.increment(
            "isa_training_completion_proof_verifications_total", status=status
        )

    def render_prometheus(self) -> str:
        lines: list[str] = [
            "# HELP isa_training_http_requests_total Training HTTP requests by method and status.",
            "# TYPE isa_training_http_requests_total counter",
        ]
        for (name, labels), value in sorted(self._counters.items()):
            lines.append(f"{name}{self._format_labels(labels)} {value}")

        for (name, labels), values in sorted(self._timings_ms.items()):
            if not values:
                continue
            lines.append(f"{name}_count{self._format_labels(labels)} {len(values)}")
            lines.append(f"{name}_sum{self._format_labels(labels)} {sum(values)}")
            lines.append(f"{name}_max{self._format_labels(labels)} {max(values)}")
        return "\n".join(lines) + "\n"

    def _label_items(
        self,
        labels: Mapping[str, str | int | bool | None],
    ) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted(
                (key, self._label_value(value))
                for key, value in labels.items()
                if value is not None and key != "amount"
            )
        )

    def _label_value(self, value: str | int | bool) -> str:
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    def _format_labels(self, labels: tuple[tuple[str, str], ...]) -> str:
        if not labels:
            return ""
        rendered = ",".join(f'{key}="{value}"' for key, value in labels)
        return f"{{{rendered}}}"
