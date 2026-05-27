"""Question-bank loader and deterministic quiz scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .catalog import DEFAULT_DATA_ROOT
from .schemas import (
    Question,
    QuestionReview,
    Quiz,
    QuizResult,
)

MODULE_SOURCE_LESSON = {
    "AI认知": "F1-L1",
    "业务": "B1-L1",
    "技术": "T1-L1",
    "治理": "G1-L1",
}

QUESTION_TYPE_MAP = {
    "单选": "single_choice",
    "多选": "multiple_choice",
    "简答": "short_answer",
}


class QuestionBank:
    """Read and score the seed assessment bank under ``_data``."""

    def __init__(self, data_root: Path | str = DEFAULT_DATA_ROOT) -> None:
        self.data_root = Path(data_root)

    def get_quiz(self, quiz_id: str) -> Quiz:
        questions = self._questions_for_quiz(quiz_id)
        return Quiz(
            id=quiz_id,
            title=self._quiz_title(quiz_id),
            questionCount=len(questions),
            questions=[self._public_question(item) for item in questions],
            scenario=self.scenario_for_quiz(quiz_id),
            variant="A",
        )

    def question_ids(self, quiz_id: str) -> list[str]:
        return [str(item["id"]) for item in self._questions_for_quiz(quiz_id)]

    def scenario_for_quiz(self, quiz_id: str) -> str:
        normalized = quiz_id.lower()
        if normalized == "entry":
            return "entry"
        if normalized == "final":
            return "final"
        if self._module_questions(quiz_id):
            return "module"
        return "practice"

    def score_attempt(
        self,
        quiz_id: str,
        attempt_id: str,
        answers: dict[str, str | list[str]],
        submitted_at: str,
    ) -> QuizResult:
        questions = self._questions_for_quiz(quiz_id)
        reviews: list[QuestionReview] = []
        correct_count = 0

        for question in questions:
            question_id = str(question["id"])
            expected = self._normalize_answer(question.get("answer"))
            actual = self._normalize_answer(answers.get(question_id))
            correct = actual == expected
            if correct:
                correct_count += 1

            reviews.append(
                QuestionReview(
                    questionId=question_id,
                    correct=correct,
                    answer=answers.get(question_id),
                    correctAnswer=question.get("answer"),
                    explanation=str(question.get("explanation") or ""),
                )
            )

        return QuizResult(
            attemptId=attempt_id,
            quizId=quiz_id,
            status="evaluated",
            score=correct_count,
            total=len(questions),
            correct=correct_count,
            reviews=reviews,
            submittedAt=submitted_at,
        )

    def _questions_for_quiz(self, quiz_id: str) -> list[dict[str, Any]]:
        payload = self._load_payload()
        normalized = quiz_id.lower()
        if normalized in payload and isinstance(payload[normalized], list):
            return [item for item in payload[normalized] if isinstance(item, dict)]

        by_module = self._module_questions(quiz_id, payload=payload)
        if by_module:
            return by_module

        raise HTTPException(status_code=404, detail=f"Quiz not found: {quiz_id}")

    def _module_questions(
        self,
        quiz_id: str,
        payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        payload = payload or self._load_payload()
        records: list[dict[str, Any]] = []
        for value in payload.values():
            if isinstance(value, list):
                records.extend(item for item in value if isinstance(item, dict))
        return [item for item in records if str(item.get("module")) == quiz_id]

    def _load_payload(self) -> dict[str, Any]:
        path = self.data_root / "questions.json"
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}

    def _public_question(self, item: dict[str, Any]) -> Question:
        module = str(item.get("module") or "")
        question_type = QUESTION_TYPE_MAP.get(
            str(item.get("type") or ""), "short_answer"
        )
        options = item.get("options")
        return Question(
            id=str(item.get("id") or ""),
            module=module,
            knowledge=str(item.get("knowledge") or ""),
            difficulty=str(item.get("difficulty") or ""),
            type=question_type,  # type: ignore[arg-type]
            stem=str(item.get("stem") or ""),
            options={
                str(key): str(value)
                for key, value in (options.items() if isinstance(options, dict) else [])
            },
            tags=[module, str(item.get("knowledge") or "")],
            sourceLessonId=MODULE_SOURCE_LESSON.get(module, "F1-L1"),
        )

    def _quiz_title(self, quiz_id: str) -> str:
        if quiz_id == "entry":
            return "Entry assessment"
        return f"{quiz_id} assessment"

    def _normalize_answer(self, value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, list):
            return tuple(
                sorted(str(item).strip().upper() for item in value if str(item).strip())
            )
        return tuple(
            sorted(
                part.strip().upper()
                for part in str(value).replace(",", "").split()
                if part.strip()
            )
        ) or (str(value).strip().upper(),)
