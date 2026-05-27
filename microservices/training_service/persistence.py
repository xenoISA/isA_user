"""Persistence adapters for training state.

The runtime currently ships with a JSON adapter for local development and test
environments. The interface is intentionally shaped around a single normalized
snapshot so it can be replaced by a training_service PostgreSQL repository
without changing the learning workflow code.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

SCHEMA_VERSION = 1
STORE_KIND = "training_service_operational_state"


@dataclass
class TrainingStateSnapshot:
    enrollments: dict[str, Any] = field(default_factory=dict)
    completed_lessons: dict[str, Any] = field(default_factory=dict)
    submissions: dict[str, Any] = field(default_factory=dict)
    quiz_attempts: dict[str, Any] = field(default_factory=dict)
    sandbox_sessions: dict[str, Any] = field(default_factory=dict)
    sandbox_evaluations: dict[str, Any] = field(default_factory=dict)
    cohorts: dict[str, Any] = field(default_factory=dict)
    completion_proofs: dict[str, Any] = field(default_factory=dict)
    path_recommendations: dict[str, Any] = field(default_factory=dict)
    assistant_interactions: list[dict[str, Any]] = field(default_factory=list)
    lesson_activity_events: list[dict[str, Any]] = field(default_factory=list)
    timeline_events: list[dict[str, Any]] = field(default_factory=list)
    lab_submissions: dict[str, Any] = field(default_factory=dict)
    review_records: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TrainingStateSnapshot":
        return cls(
            enrollments=payload.get("enrollments", {}),
            completed_lessons=payload.get("completed_lessons", {}),
            submissions=payload.get("submissions", {}),
            quiz_attempts=payload.get("quiz_attempts", {}),
            sandbox_sessions=payload.get("sandbox_sessions", {}),
            sandbox_evaluations=payload.get("sandbox_evaluations", {}),
            cohorts=payload.get("cohorts", {}),
            completion_proofs=payload.get("completion_proofs", {}),
            path_recommendations=payload.get("path_recommendations", {}),
            assistant_interactions=list(payload.get("assistant_interactions", [])),
            lesson_activity_events=list(payload.get("lesson_activity_events", [])),
            timeline_events=list(payload.get("timeline_events", [])),
            lab_submissions=payload.get("lab_submissions", {}),
            review_records=payload.get("review_records", {}),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "storeKind": STORE_KIND,
            "enrollments": self.enrollments,
            "completed_lessons": self.completed_lessons,
            "submissions": self.submissions,
            "quiz_attempts": self.quiz_attempts,
            "sandbox_sessions": self.sandbox_sessions,
            "sandbox_evaluations": self.sandbox_evaluations,
            "cohorts": self.cohorts,
            "completion_proofs": self.completion_proofs,
            "path_recommendations": self.path_recommendations,
            "assistant_interactions": self.assistant_interactions,
            "lesson_activity_events": self.lesson_activity_events,
            "timeline_events": self.timeline_events,
            "lab_submissions": self.lab_submissions,
            "review_records": self.review_records,
        }


class TrainingPersistence(Protocol):
    def load(self) -> TrainingStateSnapshot:
        """Load a normalized training state snapshot."""

    def save(self, snapshot: TrainingStateSnapshot) -> None:
        """Persist a normalized training state snapshot."""


class InMemoryTrainingPersistence:
    def __init__(self) -> None:
        self._snapshot = TrainingStateSnapshot()

    def load(self) -> TrainingStateSnapshot:
        return self._snapshot

    def save(self, snapshot: TrainingStateSnapshot) -> None:
        self._snapshot = snapshot


class JsonFileTrainingPersistence:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> TrainingStateSnapshot:
        if not self.path.exists():
            return TrainingStateSnapshot()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return TrainingStateSnapshot.from_payload(payload)

    def save(self, snapshot: TrainingStateSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                snapshot.to_payload(), ensure_ascii=False, indent=2, sort_keys=True
            ),
            encoding="utf-8",
        )


class PostgresTrainingPersistence:
    """Persist the training state snapshot in the isA_user Postgres database."""

    def __init__(
        self, database_url: str | None = None, connect_timeout: int = 5
    ) -> None:
        self.database_url = database_url or _postgres_url_from_env()
        self.connect_timeout = connect_timeout
        self._initialized = False

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - depends on runtime packaging.
            raise RuntimeError(
                "TRAINING_PERSISTENCE_BACKEND=postgres requires psycopg to be installed."
            ) from exc

        return psycopg.connect(
            self.database_url,
            connect_timeout=self.connect_timeout,
        )

    def _ensure_table(self) -> None:
        if self._initialized:
            return

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS training")
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS training.state_snapshots (
                        store_kind TEXT PRIMARY KEY,
                        schema_version INTEGER NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
        self._initialized = True

    def load(self) -> TrainingStateSnapshot:
        self._ensure_table()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT payload
                    FROM training.state_snapshots
                    WHERE store_kind = %s
                    """,
                    (STORE_KIND,),
                )
                row = cur.fetchone()
        if row is None:
            return TrainingStateSnapshot()
        payload = row[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return TrainingStateSnapshot.from_payload(dict(payload))

    def save(self, snapshot: TrainingStateSnapshot) -> None:
        self._ensure_table()
        payload = json.dumps(snapshot.to_payload(), ensure_ascii=False, sort_keys=True)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO training.state_snapshots (
                        store_kind,
                        schema_version,
                        payload,
                        updated_at
                    )
                    VALUES (%s, %s, %s::jsonb, NOW())
                    ON CONFLICT (store_kind)
                    DO UPDATE SET
                        schema_version = EXCLUDED.schema_version,
                        payload = EXCLUDED.payload,
                        updated_at = NOW()
                    """,
                    (STORE_KIND, SCHEMA_VERSION, payload),
                )


def _postgres_url_from_env() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "isa_platform")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"
