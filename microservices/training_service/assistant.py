"""Grounded deterministic assistant over course lesson text."""

from __future__ import annotations

import re

from .catalog import CourseCatalog
from .schemas import AssistantChatResponse, AssistantCitation

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "course",
    "does",
    "for",
    "in",
    "is",
    "it",
    "of",
    "on",
    "the",
    "this",
    "to",
    "tomorrow",
    "what",
    "with",
}


class CourseAssistant:
    """Retrieve grounded course passages and cite the source lesson."""

    def answer(
        self,
        catalog: CourseCatalog,
        base_path: str,
        course_id: str,
        question: str,
        lesson_id: str | None = None,
    ) -> AssistantChatResponse:
        course = catalog.get_course(course_id, base_path)
        terms = self._terms(question)
        if not terms:
            return self._fallback()

        matches: list[tuple[int, AssistantCitation]] = []
        for section in course.sections:
            for lesson in section.lessons:
                if lesson_id is not None and lesson.id != lesson_id:
                    continue

                text = f"{lesson.lesson}\n{lesson.body}\n{lesson.notes}"
                score = self._score(text, terms)
                if score <= 0:
                    continue
                matches.append(
                    (
                        score,
                        AssistantCitation(
                            courseId=course.id,
                            sectionId=section.id,
                            lessonId=lesson.id,
                            sourceAsset=lesson.sourceAsset,
                            excerpt=self._excerpt(text, terms),
                            sourceId=f"{course.id}:{section.id}:{lesson.id}",
                            score=score,
                        ),
                    )
                )

        matches.sort(key=lambda item: item[0], reverse=True)
        citations = [citation for _, citation in matches[:3]]
        if not citations and lesson_id is not None:
            return self.answer(catalog, base_path, course_id, question, lesson_id=None)
        if not citations:
            return self._fallback()

        return AssistantChatResponse(
            status="answered",
            answer=(
                "Retrieved grounded course material for this answer. The strongest source is "
                f"{citations[0].sourceId}; use the cited excerpt to guide your own work."
            ),
            citations=citations,
        )

    def _fallback(self) -> AssistantChatResponse:
        return AssistantChatResponse(
            status="fallback",
            answer=(
                "I can only answer from the available training course material. "
                "No grounded citation was found for that question."
            ),
            citations=[],
            fallbackReason="no_grounded_source",
        )

    def _terms(self, question: str) -> set[str]:
        raw_terms = re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", question.lower())
        return {term for term in raw_terms if term not in STOP_WORDS and len(term) >= 2}

    def _score(self, text: str, terms: set[str]) -> int:
        normalized = text.lower()
        return sum(1 for term in terms if term in normalized)

    def _excerpt(self, text: str, terms: set[str]) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            if any(term in line.lower() for term in terms):
                return line[:280]
        return (lines[0] if lines else "")[:280]
