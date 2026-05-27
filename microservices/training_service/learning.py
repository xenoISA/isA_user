"""Learner workflow state for the training MVP."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from .catalog import CourseCatalog
from .persistence import (
    InMemoryTrainingPersistence,
    JsonFileTrainingPersistence,
    TrainingPersistence,
    TrainingStateSnapshot,
)
from .schemas import (
    ActiveCourseProgress,
    Cohort,
    CohortDashboard,
    CompletionProof,
    CompletionProofVerification,
    Enrollment,
    LabDefinition,
    LabSubmissionResult,
    LessonActivityEvent,
    LessonProgress,
    LearnerCourseSummary,
    OrganizationDashboard,
    OrganizationReport,
    PathRecommendation,
    RolePolicy,
    SandboxAuditEvent,
    SandboxEvaluation,
    SandboxSession,
    Submission,
    TrainingTimelineEvent,
    TrainingProgress,
)
from .sandbox_lab_adapter import is_agent_sdk_lab_task, run_agent_sdk_lab_task
from .sandbox_runner import run_agent_artifact


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1(":".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


class TrainingStateStore:
    """Training workflow state backed by memory or a JSON persistence file."""

    def __init__(
        self,
        storage_path: str | Path | None = None,
        persistence: TrainingPersistence | None = None,
        sandbox_execution_enabled: bool = True,
    ) -> None:
        if persistence is not None and storage_path is not None:
            raise ValueError("Pass either persistence or storage_path, not both.")
        if persistence is None:
            persistence = (
                JsonFileTrainingPersistence(storage_path)
                if storage_path is not None
                else InMemoryTrainingPersistence()
            )
        self.persistence = persistence
        self.sandbox_execution_enabled = sandbox_execution_enabled
        self._enrollments: dict[str, dict[str, Enrollment]] = {}
        self._completed_lessons: dict[str, dict[str, set[str]]] = {}
        self._submissions: dict[str, list[Submission]] = {}
        self._quiz_attempts: dict[str, dict[str, object]] = {}
        self._sandbox_sessions: dict[str, dict[str, object]] = {}
        self._sandbox_evaluations: dict[str, SandboxEvaluation] = {}
        self._cohorts: dict[str, Cohort] = {}
        self._completion_proofs: dict[str, CompletionProof] = {}
        self._path_recommendations: dict[str, PathRecommendation] = {}
        self._assistant_interactions: list[dict[str, object]] = []
        self._lesson_activity_events: list[LessonActivityEvent] = []
        self._timeline_events: list[TrainingTimelineEvent] = []
        self._lab_submissions: dict[str, LabSubmissionResult] = {}
        self._review_records: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        snapshot = self.persistence.load()
        self._enrollments = {
            user_id: {
                course_id: Enrollment.model_validate(enrollment)
                for course_id, enrollment in courses.items()
            }
            for user_id, courses in snapshot.enrollments.items()
        }
        self._completed_lessons = {
            user_id: {course_id: set(lessons) for course_id, lessons in courses.items()}
            for user_id, courses in snapshot.completed_lessons.items()
        }
        self._submissions = {
            user_id: [Submission.model_validate(item) for item in submissions]
            for user_id, submissions in snapshot.submissions.items()
        }
        self._quiz_attempts = {
            attempt_id: dict(attempt)
            for attempt_id, attempt in snapshot.quiz_attempts.items()
        }
        self._sandbox_sessions = {
            session_id: {
                **record,
                "session": SandboxSession.model_validate(record["session"]),
            }
            for session_id, record in snapshot.sandbox_sessions.items()
        }
        self._sandbox_evaluations = {
            session_id: SandboxEvaluation.model_validate(evaluation)
            for session_id, evaluation in snapshot.sandbox_evaluations.items()
        }
        self._cohorts = {
            cohort_id: Cohort.model_validate(cohort)
            for cohort_id, cohort in snapshot.cohorts.items()
        }
        self._completion_proofs = {
            proof_id: CompletionProof.model_validate(proof)
            for proof_id, proof in snapshot.completion_proofs.items()
        }
        self._path_recommendations = {
            recommendation_id: PathRecommendation.model_validate(recommendation)
            for recommendation_id, recommendation in snapshot.path_recommendations.items()
        }
        self._assistant_interactions = list(snapshot.assistant_interactions)
        self._lesson_activity_events = [
            LessonActivityEvent.model_validate(event)
            for event in snapshot.lesson_activity_events
        ]
        self._timeline_events = [
            TrainingTimelineEvent.model_validate(event)
            for event in snapshot.timeline_events
        ]
        self._lab_submissions = {
            submission_id: LabSubmissionResult.model_validate(submission)
            for submission_id, submission in snapshot.lab_submissions.items()
        }
        self._review_records = {
            review_id: dict(review)
            for review_id, review in snapshot.review_records.items()
        }

    def _flush(self) -> None:
        self.persistence.save(
            TrainingStateSnapshot(
                enrollments={
                    user_id: {
                        course_id: enrollment.model_dump(mode="json")
                        for course_id, enrollment in courses.items()
                    }
                    for user_id, courses in self._enrollments.items()
                },
                completed_lessons={
                    user_id: {
                        course_id: sorted(lessons)
                        for course_id, lessons in courses.items()
                    }
                    for user_id, courses in self._completed_lessons.items()
                },
                submissions={
                    user_id: [
                        submission.model_dump(mode="json") for submission in submissions
                    ]
                    for user_id, submissions in self._submissions.items()
                },
                quiz_attempts=self._quiz_attempts,
                sandbox_sessions={
                    session_id: {
                        **{
                            key: value
                            for key, value in record.items()
                            if key != "session"
                        },
                        "session": record["session"].model_dump(mode="json"),
                    }
                    for session_id, record in self._sandbox_sessions.items()
                },
                sandbox_evaluations={
                    session_id: evaluation.model_dump(mode="json")
                    for session_id, evaluation in self._sandbox_evaluations.items()
                },
                cohorts={
                    cohort_id: cohort.model_dump(mode="json")
                    for cohort_id, cohort in self._cohorts.items()
                },
                completion_proofs={
                    proof_id: proof.model_dump(mode="json")
                    for proof_id, proof in self._completion_proofs.items()
                },
                path_recommendations={
                    recommendation_id: recommendation.model_dump(mode="json")
                    for recommendation_id, recommendation in self._path_recommendations.items()
                },
                assistant_interactions=[
                    dict(item) for item in self._assistant_interactions
                ],
                lesson_activity_events=[
                    event.model_dump(mode="json")
                    for event in self._lesson_activity_events
                ],
                timeline_events=[
                    event.model_dump(mode="json") for event in self._timeline_events
                ],
                lab_submissions={
                    submission_id: submission.model_dump(mode="json")
                    for submission_id, submission in self._lab_submissions.items()
                },
                review_records=self._review_records,
            )
        )

    def _record_timeline_event(
        self,
        learner_id: str,
        event_type: str,
        source: str,
        actor_id: str,
        course_id: str | None = None,
        cohort_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TrainingTimelineEvent:
        now = utc_now()
        event = TrainingTimelineEvent(
            id=stable_id(
                "tl",
                learner_id,
                event_type,
                source,
                course_id or "",
                cohort_id or "",
                now,
            ),
            learnerId=learner_id,
            eventType=event_type,
            source=source,
            actorId=actor_id,
            courseId=course_id.upper() if course_id else None,
            cohortId=cohort_id,
            metadata=metadata or {},
            createdAt=now,
        )
        self._timeline_events.append(event)
        return event

    def timeline_for_learner(self, learner_id: str) -> list[TrainingTimelineEvent]:
        return sorted(
            (event for event in self._timeline_events if event.learnerId == learner_id),
            key=lambda event: event.createdAt,
        )

    def record_assistant_interaction(
        self,
        user_id: str,
        course_id: str,
        lesson_id: str | None,
        status: str,
        citation_count: int,
        request_id: str,
    ) -> None:
        self._assistant_interactions.append(
            {
                "id": stable_id("assist", user_id, course_id.upper(), request_id),
                "learnerId": user_id,
                "courseId": course_id.upper(),
                "lessonId": lesson_id,
                "status": status,
                "citationCount": citation_count,
                "requestId": request_id,
                "createdAt": utc_now(),
            }
        )
        self._flush()

    def record_lesson_activity(
        self,
        user_id: str,
        course_id: str,
        lesson_id: str,
        activity_type: str,
        catalog: CourseCatalog,
        base_path: str,
        position_seconds: int | None = None,
        asset_key: str | None = None,
        required: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> LessonActivityEvent:
        course_id = course_id.upper()
        detail = catalog.get_course(course_id, base_path)
        lesson_ids = {
            lesson.id for section in detail.sections for lesson in section.lessons
        }
        if course_id not in self._enrollments.get(user_id, {}):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Enroll in this course before recording lesson activity.",
            )
        if lesson_id not in lesson_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson not found: {lesson_id}",
            )

        now = utc_now()
        event = LessonActivityEvent(
            id=stable_id("act", user_id, course_id, lesson_id, activity_type, now),
            learnerId=user_id,
            courseId=course_id,
            lessonId=lesson_id,
            activityType=activity_type,
            positionSeconds=position_seconds,
            assetKey=asset_key,
            required=required,
            metadata=metadata or {},
            createdAt=now,
        )
        self._lesson_activity_events.append(event)
        enrollment = self._enrollments[user_id][course_id]
        self._enrollments[user_id][course_id] = enrollment.model_copy(
            update={"lastActivityAt": now}
        )
        self._flush()
        return event

    def enroll(
        self,
        user_id: str,
        course_id: str,
        catalog: CourseCatalog,
        base_path: str,
    ) -> Enrollment:
        catalog.get_course(course_id, base_path)
        course_id = course_id.upper()
        user_enrollments = self._enrollments.setdefault(user_id, {})
        existing = user_enrollments.get(course_id)
        if existing is not None:
            return existing

        now = utc_now()
        enrollment = Enrollment(
            id=stable_id("enr", user_id, course_id),
            courseId=course_id,
            status="active",
            startedAt=now,
            completedAt=None,
            lastActivityAt=now,
        )
        user_enrollments[course_id] = enrollment
        self._completed_lessons.setdefault(user_id, {}).setdefault(course_id, set())
        self._flush()
        return enrollment

    def progress(
        self,
        user_id: str,
        catalog: CourseCatalog,
        base_path: str,
    ) -> TrainingProgress:
        enrollments = list(self._enrollments.get(user_id, {}).values())
        active_courses: list[ActiveCourseProgress] = []
        lesson_progress: dict[str, LessonProgress] = {}
        total_lessons = 0
        completed_lessons = 0

        for enrollment in enrollments:
            detail = catalog.get_course(enrollment.courseId, base_path)
            lesson_ids = [
                lesson.id for section in detail.sections for lesson in section.lessons
            ]
            completed = sorted(
                self._completed_lessons.get(user_id, {})
                .get(enrollment.courseId, set())
                .intersection(lesson_ids)
            )
            total = len(lesson_ids)
            complete_count = len(completed)
            total_lessons += total
            completed_lessons += complete_count
            next_lesson = next(
                (lesson_id for lesson_id in lesson_ids if lesson_id not in completed),
                None,
            )
            percent = round((complete_count / total) * 100) if total else 0

            lesson_progress[enrollment.courseId] = LessonProgress(
                completedLessons=completed,
                totalLessons=total,
                percentComplete=percent,
                resumeLessonId=self._resume_lesson_id(user_id, enrollment.courseId),
                lastActivityAt=self._last_lesson_activity_at(
                    user_id, enrollment.courseId
                ),
                activityEvents=self._lesson_events(user_id, enrollment.courseId),
            )
            active_courses.append(
                ActiveCourseProgress(
                    courseId=enrollment.courseId,
                    enrollmentId=enrollment.id,
                    status=enrollment.status,
                    completedLessonCount=complete_count,
                    totalLessonCount=total,
                    nextLessonId=next_lesson,
                )
            )

        completion_percent = (
            round((completed_lessons / total_lessons) * 100) if total_lessons else 0
        )
        return TrainingProgress(
            enrollments=enrollments,
            activeCourses=active_courses,
            lessonProgress=lesson_progress,
            quizState=self.quiz_state(user_id),
            completionPercent=completion_percent,
        )

    def submit_work(
        self,
        user_id: str,
        course_id: str,
        lesson_id: str,
        content: str,
        catalog: CourseCatalog,
        base_path: str,
    ) -> Submission:
        course_id = course_id.upper()
        detail = catalog.get_course(course_id, base_path)
        lesson_ids = {
            lesson.id for section in detail.sections for lesson in section.lessons
        }
        if course_id not in self._enrollments.get(user_id, {}):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Enroll in this course before submitting work.",
            )
        if lesson_id not in lesson_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson not found: {lesson_id}",
            )

        now = utc_now()
        content_score = (
            min(100, max(50, len(content.strip()) // 4)) if content.strip() else 0
        )
        submission = Submission(
            id=stable_id("sub", user_id, course_id, lesson_id, now),
            courseId=course_id,
            lessonId=lesson_id,
            status="evaluated" if content.strip() else "rejected",
            score=content_score,
            feedback=(
                "Submission recorded and lesson progress updated."
                if content.strip()
                else "Submission content is empty."
            ),
            submittedAt=now,
        )
        self._submissions.setdefault(user_id, []).append(submission)
        if submission.status == "evaluated":
            self._completed_lessons.setdefault(user_id, {}).setdefault(
                course_id,
                set(),
            ).add(lesson_id)
            enrollment = self._enrollments[user_id][course_id]
            self._enrollments[user_id][course_id] = enrollment.model_copy(
                update={"lastActivityAt": now}
            )
            self.record_lesson_activity(
                user_id=user_id,
                course_id=course_id,
                lesson_id=lesson_id,
                activity_type="lesson_completed",
                catalog=catalog,
                base_path=base_path,
                required=True,
                metadata={"submissionId": submission.id},
            )
        else:
            self._flush()
        return submission

    def _lesson_events(self, user_id: str, course_id: str) -> list[LessonActivityEvent]:
        return [
            event
            for event in self._lesson_activity_events
            if event.learnerId == user_id and event.courseId == course_id
        ]

    def _resume_lesson_id(self, user_id: str, course_id: str) -> str | None:
        events = self._lesson_events(user_id, course_id)
        return events[-1].lessonId if events else None

    def _last_lesson_activity_at(self, user_id: str, course_id: str) -> str | None:
        events = self._lesson_events(user_id, course_id)
        return events[-1].createdAt if events else None

    def create_quiz_attempt(
        self,
        user_id: str,
        quiz_id: str,
        question_ids: list[str],
        scenario: str = "practice",
        variant: str = "A",
    ) -> dict[str, object]:
        now = utc_now()
        attempt = {
            "id": stable_id("qat", user_id, quiz_id, now),
            "user_id": user_id,
            "quiz_id": quiz_id,
            "question_ids": list(question_ids),
            "status": "in_progress",
            "started_at": now,
            "submitted_at": None,
            "answers": {},
            "scenario": scenario,
            "variant": variant,
        }
        self._quiz_attempts[str(attempt["id"])] = attempt
        self._flush()
        return attempt

    def get_owned_quiz_attempt(
        self, user_id: str, attempt_id: str
    ) -> dict[str, object]:
        attempt = self._quiz_attempts.get(attempt_id)
        if attempt is None:
            raise HTTPException(
                status_code=404, detail=f"Quiz attempt not found: {attempt_id}"
            )
        if attempt["user_id"] != user_id:
            raise HTTPException(
                status_code=403, detail="Quiz attempt belongs to another user."
            )
        return attempt

    def update_quiz_attempt(
        self,
        attempt_id: str,
        answers: dict[str, str | list[str]],
    ) -> str:
        now = utc_now()
        attempt = self._quiz_attempts[attempt_id]
        attempt["status"] = "evaluated"
        attempt["submitted_at"] = now
        attempt["answers"] = answers
        self._flush()
        return now

    def record_quiz_result(
        self,
        attempt_id: str,
        score: int,
        total: int,
        correct: int,
        reviews: list[dict[str, Any]] | None = None,
    ) -> None:
        attempt = self._quiz_attempts[attempt_id]
        attempt["score"] = score
        attempt["total"] = total
        attempt["correct"] = correct
        attempt["reviews"] = reviews or []
        self._flush()

    def quiz_state(self, user_id: str) -> dict[str, object]:
        state: dict[str, object] = {}
        for attempt in self._quiz_attempts.values():
            if attempt["user_id"] != user_id:
                continue
            state[str(attempt["quiz_id"])] = {
                "attemptId": attempt["id"],
                "status": attempt["status"],
                "submittedAt": attempt["submitted_at"],
                "score": attempt.get("score"),
                "total": attempt.get("total"),
            }
        return state

    def path_recommendation(
        self,
        user_id: str,
        attempt_id: str,
        role: str,
    ) -> PathRecommendation:
        attempt = self.get_owned_quiz_attempt(user_id, attempt_id)
        if attempt.get("status") != "evaluated":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Submit the entry assessment before requesting a path recommendation.",
            )

        dimension_scores = self._dimension_scores(attempt)
        role_normalized = role.strip().lower() or "developer"
        average = (
            round(sum(dimension_scores.values()) / len(dimension_scores))
            if dimension_scores
            else 0
        )
        weakest = sorted(dimension_scores.items(), key=lambda item: item[1])[:1]

        if role_normalized in {"engineer", "developer", "technical"} and average >= 75:
            path_code = "T"
            start_course = "T1"
            skipped = ["F0"]
        else:
            path_code = "F"
            start_course = "F1"
            skipped = []

        reinforcement = [
            self._module_reinforcement_course(module)
            for module, score in weakest
            if score < 70
        ]
        recommendation = PathRecommendation(
            id=stable_id("path", user_id, attempt_id, role_normalized),
            learnerId=user_id,
            role=role_normalized,
            attemptId=attempt_id,
            recommendedPathCode=path_code,
            startCourseId=start_course,
            skippedCourseIds=skipped,
            reinforcementCourseIds=list(dict.fromkeys(reinforcement)),
            dimensionScores=dimension_scores,
            rationale=[
                f"Entry assessment average is {average}%.",
                f"Role '{role_normalized}' maps to the {path_code} path.",
            ],
            createdAt=utc_now(),
        )
        self._path_recommendations[recommendation.id] = recommendation
        self._flush()
        return recommendation

    def _dimension_scores(self, attempt: dict[str, object]) -> dict[str, int]:
        reviews = attempt.get("reviews")
        if not isinstance(reviews, list):
            reviews = []
        scores: dict[str, list[int]] = {}
        for review in reviews:
            if not isinstance(review, dict):
                continue
            question_id = str(review.get("questionId") or "")
            module = self._entry_dimension(question_id)
            if module is None:
                continue
            correct = bool(review.get("correct"))
            scores.setdefault(module, []).append(100 if correct else 0)
        return {
            module: round(sum(values) / len(values))
            for module, values in scores.items()
            if values
        }

    def _entry_dimension(self, question_id: str) -> str | None:
        if not question_id.startswith("R"):
            return None
        try:
            number = int(question_id[1:])
        except ValueError:
            return None
        if 1 <= number <= 10:
            return "AI认知"
        if 11 <= number <= 20:
            return "业务"
        if 21 <= number <= 30:
            return "技术"
        if 31 <= number <= 40:
            return "治理"
        return None

    def _module_reinforcement_course(self, module: str) -> str:
        return {
            "AI认知": "F1",
            "业务": "B1",
            "技术": "T1",
            "治理": "G1",
        }.get(module, "F1")

    def best_quiz_score_percent(self, user_id: str) -> int | None:
        best: int | None = None
        for attempt in self._quiz_attempts.values():
            if attempt["user_id"] != user_id:
                continue
            total = attempt.get("total")
            score = attempt.get("score")
            if not isinstance(total, int) or not isinstance(score, int) or total <= 0:
                continue
            percent = round((score / total) * 100)
            best = percent if best is None else max(best, percent)
        return best

    def lab_status(self, user_id: str, course_id: str) -> str:
        for submission in self._lab_submissions.values():
            if (
                submission.learnerId == user_id
                and submission.courseId == course_id
                and (
                    submission.passed
                    or self._review_records.get(submission.submissionId, {}).get(
                        "passed"
                    )
                    is True
                )
            ):
                return "passed"
        for evaluation in self._sandbox_evaluations.values():
            session = self._sandbox_sessions.get(evaluation.sessionId, {}).get(
                "session"
            )
            if (
                isinstance(session, SandboxSession)
                and session.courseId == course_id
                and self._sandbox_sessions[evaluation.sessionId].get("user_id")
                == user_id
                and evaluation.passed
            ):
                return "passed"
        for submission in self._submissions.get(user_id, []):
            if (
                submission.courseId == course_id
                and submission.status == "evaluated"
                and submission.score >= 50
            ):
                return "passed"
        return "missing"

    def lab_definition(self, lab_id: str) -> LabDefinition:
        if lab_id != "F1-agent-hello":
            raise HTTPException(status_code=404, detail=f"Lab not found: {lab_id}")
        return LabDefinition(
            id=lab_id,
            title="Agent hello-world lab",
            courseId="F1",
            lessonId="F1-L1",
            setup=[{"name": "Prepare isA_Agent_SDK hello task"}],
            task={
                "type": "isa_agent_sdk_task",
                "sdk": "isA_Agent_SDK",
                "run": {
                    "entrypoint": "handler",
                    "input": {"input": "hello", "source": "offline_training_lab"},
                },
                "evaluation": {
                    "passingScore": 80,
                    "proofEligible": True,
                    "rubric": [
                        {
                            "id": "hello_output",
                            "points": 80,
                            "requiresOutputContains": "hello",
                        }
                    ],
                },
            },
            rubric=[
                {
                    "id": "hello_output",
                    "points": 80,
                    "requiresOutputContains": "hello",
                }
            ],
            artifactSchema={
                "kind": "python_handler",
                "required": ["handler_or_RESULT"],
            },
            resourceLimits={"timeoutSeconds": 300, "network": "disabled"},
            passingScore=80,
            proofEligible=True,
        )

    def submit_lab(
        self,
        lab_id: str,
        learner_id: str,
        artifact: str,
        metadata: dict[str, Any] | None = None,
    ) -> LabSubmissionResult:
        lab = self.lab_definition(lab_id)
        if lab.courseId not in self._enrollments.get(learner_id, {}):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Enroll in this course before submitting a lab.",
            )
        task = lab.task
        sdk_task = {
            **task,
            "evaluation": {
                **dict(task.get("evaluation", {})),
                "rubric": lab.rubric,
                "passingScore": lab.passingScore,
                "proofEligible": lab.proofEligible,
            },
        }
        result = run_agent_sdk_lab_task(
            task=sdk_task,
            artifact=artifact,
            timeout_seconds=int(lab.resourceLimits.get("timeoutSeconds", 300)),
        )
        now = utc_now()
        submission_id = stable_id("lab", learner_id, lab_id, now)
        audit_event = SandboxAuditEvent(
            action="lab_submitted",
            at=now,
            actorId=learner_id,
        )
        submission = LabSubmissionResult(
            submissionId=submission_id,
            labId=lab_id,
            learnerId=learner_id,
            courseId=lab.courseId,
            sessionId=submission_id,
            status="evaluated",
            score=result.score,
            passed=result.passed,
            executed=result.executed,
            feedback=result.feedback,
            auditTrail=[audit_event],
            executionLog=result.executionLog,
            resourceUsage=result.resourceUsage,
            artifacts=result.artifacts,
            rubricFeedback=[
                {
                    "id": item.id,
                    "passed": item.passed,
                    "pointsAwarded": item.pointsAwarded,
                    "pointsAvailable": item.pointsAvailable,
                    "feedback": item.feedback,
                }
                for item in result.rubricFeedback
            ],
            proofEligible=result.proofEligible,
            adapter=result.adapter,
            reviewStatus="approved" if result.passed else "pending_review",
        )
        self._lab_submissions[submission_id] = submission
        self._review_records[submission_id] = {
            "id": submission_id,
            "sourceType": "lab_submission",
            "learnerId": learner_id,
            "courseId": lab.courseId,
            "labId": lab_id,
            "status": "pending_review" if not result.passed else "approved",
            "score": result.score,
            "passed": result.passed,
            "createdAt": now,
            "finalStatus": "approved" if result.passed else None,
            "overrideReason": None,
        }
        self._record_timeline_event(
            learner_id=learner_id,
            event_type="lab_submitted",
            source="lab",
            actor_id=learner_id,
            course_id=lab.courseId,
            metadata={
                "labId": lab_id,
                "submissionId": submission_id,
                **(metadata or {}),
            },
        )
        self._flush()
        return submission

    def review_queue(self) -> list[dict[str, Any]]:
        return [
            dict(record)
            for record in self._review_records.values()
            if record.get("status") == "pending_review"
            or record.get("finalStatus") is not None
        ]

    def override_review_item(
        self,
        item_id: str,
        final_status: str,
        score: int | None,
        passed: bool | None,
        reason: str,
        actor_id: str,
    ) -> dict[str, Any]:
        record = self._review_records.get(item_id)
        if record is None:
            raise HTTPException(
                status_code=404, detail=f"Review item not found: {item_id}"
            )
        if score is not None:
            record["score"] = score
        if passed is not None:
            record["passed"] = passed
        record["finalStatus"] = final_status
        record["overrideReason"] = reason
        record["overrideActorId"] = actor_id
        record["overriddenAt"] = utc_now()
        submission = self._lab_submissions.get(item_id)
        if submission is not None:
            self._lab_submissions[item_id] = submission.model_copy(
                update={
                    "score": record["score"],
                    "passed": bool(record["passed"]),
                    "proofEligible": bool(record["passed"]),
                    "reviewStatus": final_status,
                }
            )
        self._record_timeline_event(
            learner_id=str(record["learnerId"]),
            event_type=f"review_{final_status}",
            source="review",
            actor_id=actor_id,
            course_id=str(record.get("courseId") or ""),
            metadata={"reviewItemId": item_id, "reason": reason},
        )
        self._flush()
        return dict(record)

    def completion_eligibility(
        self,
        user_id: str,
        course_id: str,
        catalog: CourseCatalog,
        base_path: str,
    ) -> dict[str, object]:
        course_id = course_id.upper()
        progress = self.progress(user_id, catalog, base_path)
        course_progress = progress.lessonProgress.get(course_id)
        progress_percent = course_progress.percentComplete if course_progress else 0
        quiz_score = self.best_quiz_score_percent(user_id)
        lab_status = self.lab_status(user_id, course_id)
        attendance_status = self.attendance_status(user_id, course_id)
        missing: list[str] = []

        if attendance_status == "missing":
            missing.append("Required offline attendance must be present.")
        if progress_percent < 100:
            missing.append("Course progress must be 100%.")
        if quiz_score is None or quiz_score < 60:
            missing.append("Required quiz score must be at least 60%.")
        if lab_status != "passed":
            missing.append("Required lab outcome must be passed.")

        return {
            "eligible": not missing,
            "missing": missing,
            "progressPercent": progress_percent,
            "quizScorePercent": quiz_score or 0,
            "labStatus": lab_status,
            "attendanceStatus": attendance_status,
        }

    def attendance_status(self, user_id: str, course_id: str) -> str:
        course_id = course_id.upper()
        requires_attendance = any(
            user_id in cohort.learnerIds and course_id in cohort.courseIds
            for cohort in self._cohorts.values()
        )
        if not requires_attendance:
            return "not_required"
        for event in reversed(self._timeline_events):
            if event.learnerId != user_id or event.courseId != course_id:
                continue
            if event.eventType == "attendance_present":
                return "present"
            if event.eventType in {"attendance_absent", "attendance_excused"}:
                return "missing"
        return "missing"

    def completion_proof(
        self,
        user_id: str,
        course_id: str,
        catalog: CourseCatalog,
        base_path: str,
    ) -> CompletionProof:
        course_id = course_id.upper()
        catalog.get_course(course_id, base_path)
        eligibility = self.completion_eligibility(
            user_id, course_id, catalog, base_path
        )
        if not eligibility["eligible"]:
            raise HTTPException(status_code=409, detail=eligibility)

        proof_id = stable_id("proof", user_id, course_id)
        existing = self._completion_proofs.get(proof_id)
        if existing is not None:
            return existing

        now = utc_now()
        proof = CompletionProof(
            id=proof_id,
            type="completion_proof",
            learnerId=user_id,
            courseId=course_id,
            issuedAt=now,
            progressPercent=int(eligibility["progressPercent"]),
            quizScorePercent=int(eligibility["quizScorePercent"]),
            labStatus="passed",
            verification=CompletionProofVerification(
                status="verifiable",
                code=f"isa-proof-{stable_id('v', user_id, course_id)[2:]}",
                method="sha1:user-course-stable-id",
            ),
        )
        self._completion_proofs[proof_id] = proof
        self._flush()
        return proof

    def verify_completion_proof(self, proof_id_or_code: str) -> CompletionProof | None:
        proof = self._completion_proofs.get(proof_id_or_code)
        if proof is not None:
            return proof
        for candidate in self._completion_proofs.values():
            if candidate.verification.code == proof_id_or_code:
                return candidate
        return None

    def create_cohort(
        self,
        organization_id: str,
        name: str,
        path_code: str,
        course_ids: list[str],
        learner_ids: list[str],
        start_at: str | None = None,
        end_at: str | None = None,
        delivery_status: str = "scheduled",
    ) -> Cohort:
        now = utc_now()
        normalized_course_ids = [course_id.upper() for course_id in course_ids]
        normalized_learner_ids = list(dict.fromkeys(learner_ids))
        cohort = Cohort(
            id=stable_id("cohort", organization_id, name, now),
            organizationId=organization_id,
            name=name,
            pathCode=path_code,
            courseIds=normalized_course_ids,
            learnerIds=normalized_learner_ids,
            createdAt=now,
            startAt=start_at,
            endAt=end_at,
            deliveryStatus=delivery_status,  # type: ignore[arg-type]
            rolePolicy=RolePolicy(
                create=["org_admin", "operator"],
                read=["org_admin", "operator", "teacher"],
                review=["teacher", "operator"],
            ),
        )
        self._cohorts[cohort.id] = cohort
        for learner_id in normalized_learner_ids:
            self._assign_learner_to_courses(
                learner_id=learner_id,
                course_ids=normalized_course_ids,
                actor_id="system",
                cohort_id=cohort.id,
            )
        self._flush()
        return cohort

    def assign_learners_to_cohort(
        self,
        cohort_id: str,
        learner_ids: list[str],
        actor_id: str,
    ) -> Cohort:
        cohort = self._get_cohort(cohort_id)
        merged = list(dict.fromkeys([*cohort.learnerIds, *learner_ids]))
        updated = cohort.model_copy(update={"learnerIds": merged})
        self._cohorts[cohort_id] = updated
        for learner_id in learner_ids:
            self._assign_learner_to_courses(
                learner_id=learner_id,
                course_ids=updated.courseIds,
                actor_id=actor_id,
                cohort_id=cohort_id,
            )
        self._flush()
        return updated

    def _assign_learner_to_courses(
        self,
        learner_id: str,
        course_ids: list[str],
        actor_id: str,
        cohort_id: str,
    ) -> None:
        enrollments = self._enrollments.setdefault(learner_id, {})
        completed = self._completed_lessons.setdefault(learner_id, {})
        for course_id in course_ids:
            normalized_course_id = course_id.upper()
            if normalized_course_id not in enrollments:
                now = utc_now()
                enrollments[normalized_course_id] = Enrollment(
                    id=stable_id("enr", learner_id, normalized_course_id),
                    courseId=normalized_course_id,
                    status="active",
                    startedAt=now,
                    completedAt=None,
                    lastActivityAt=now,
                )
                completed.setdefault(normalized_course_id, set())
            self._record_timeline_event(
                learner_id=learner_id,
                event_type="cohort_assigned",
                source="cohort",
                actor_id=actor_id,
                course_id=normalized_course_id,
                cohort_id=cohort_id,
            )

    def record_attendance(
        self,
        cohort_id: str,
        learner_id: str,
        course_id: str,
        attendance_status: str,
        actor_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> TrainingTimelineEvent:
        cohort = self._get_cohort(cohort_id)
        normalized_course_id = course_id.upper()
        if learner_id not in cohort.learnerIds:
            raise HTTPException(
                status_code=404, detail=f"Learner not in cohort: {learner_id}"
            )
        if normalized_course_id not in cohort.courseIds:
            raise HTTPException(
                status_code=404, detail=f"Course not in cohort: {normalized_course_id}"
            )
        event = self._record_timeline_event(
            learner_id=learner_id,
            event_type=f"attendance_{attendance_status}",
            source="attendance",
            actor_id=actor_id,
            course_id=normalized_course_id,
            cohort_id=cohort_id,
            metadata=metadata,
        )
        self._flush()
        return event

    def _get_cohort(self, cohort_id: str) -> Cohort:
        cohort = self._cohorts.get(cohort_id)
        if cohort is None:
            raise HTTPException(
                status_code=404, detail=f"Cohort not found: {cohort_id}"
            )
        return cohort

    def organization_dashboard(
        self,
        organization_id: str,
        catalog: CourseCatalog,
        base_path: str,
    ) -> OrganizationDashboard:
        dashboards = [
            self._cohort_dashboard(cohort, catalog, base_path)
            for cohort in self._cohorts.values()
            if cohort.organizationId == organization_id
        ]
        return OrganizationDashboard(
            organizationId=organization_id,
            featureFlag="training_enterprise_dashboard",
            cohorts=dashboards,
        )

    def organization_report(
        self,
        organization_id: str,
        catalog: CourseCatalog,
        base_path: str,
    ) -> OrganizationReport:
        columns = [
            "organization_id",
            "cohort_id",
            "learner_id",
            "course_id",
            "progress_percent",
            "quiz_score_percent",
            "lab_status",
        ]
        rows: list[dict[str, str | int | None]] = []
        for cohort in self._cohorts.values():
            if cohort.organizationId != organization_id:
                continue
            for learner in self._cohort_learners(cohort, catalog, base_path):
                rows.append(
                    {
                        "organization_id": organization_id,
                        "cohort_id": cohort.id,
                        "learner_id": learner.learnerId,
                        "course_id": learner.courseId,
                        "progress_percent": learner.progressPercent,
                        "quiz_score_percent": learner.quizScorePercent,
                        "lab_status": learner.labStatus,
                    }
                )

        return OrganizationReport(
            organizationId=organization_id,
            format="csv",
            columns=columns,
            rows=rows,
        )

    def course_learners(
        self,
        course_id: str,
        catalog: CourseCatalog,
        base_path: str,
    ) -> list[LearnerCourseSummary]:
        course_id = course_id.upper()
        learners: list[LearnerCourseSummary] = []
        for user_id, enrollments in self._enrollments.items():
            if course_id not in enrollments:
                continue
            learners.append(
                self._learner_summary(user_id, course_id, catalog, base_path)
            )
        return learners

    def review_activity(self) -> dict[str, list[dict[str, object]]]:
        quiz_attempts = [
            {
                "attemptId": attempt["id"],
                "learnerId": attempt["user_id"],
                "quizId": attempt["quiz_id"],
                "status": attempt["status"],
                "score": attempt.get("score"),
                "total": attempt.get("total"),
                "submittedAt": attempt.get("submitted_at"),
            }
            for attempt in self._quiz_attempts.values()
        ]
        lab_submissions = [
            {
                "submissionId": submission.id,
                "learnerId": user_id,
                "courseId": submission.courseId,
                "lessonId": submission.lessonId,
                "status": submission.status,
                "score": submission.score,
                "submittedAt": submission.submittedAt,
            }
            for user_id, submissions in self._submissions.items()
            for submission in submissions
        ]
        return {
            "quizAttempts": quiz_attempts,
            "labSubmissions": lab_submissions,
            "flaggedAssistantSessions": [
                dict(item) for item in self._assistant_interactions
            ],
        }

    def _cohort_dashboard(
        self,
        cohort: Cohort,
        catalog: CourseCatalog,
        base_path: str,
    ) -> CohortDashboard:
        learners = self._cohort_learners(cohort, catalog, base_path)
        completion_percent = (
            round(sum(learner.progressPercent for learner in learners) / len(learners))
            if learners
            else 0
        )
        return CohortDashboard(
            cohortId=cohort.id,
            name=cohort.name,
            completionPercent=completion_percent,
            learners=learners,
        )

    def _cohort_learners(
        self,
        cohort: Cohort,
        catalog: CourseCatalog,
        base_path: str,
    ) -> list[LearnerCourseSummary]:
        summaries: list[LearnerCourseSummary] = []
        for learner_id in cohort.learnerIds:
            for course_id in cohort.courseIds:
                summaries.append(
                    self._learner_summary(learner_id, course_id, catalog, base_path)
                )
        return summaries

    def _learner_summary(
        self,
        user_id: str,
        course_id: str,
        catalog: CourseCatalog,
        base_path: str,
    ) -> LearnerCourseSummary:
        progress = self.progress(user_id, catalog, base_path)
        course_progress = progress.lessonProgress.get(course_id)
        return LearnerCourseSummary(
            learnerId=user_id,
            courseId=course_id,
            progressPercent=course_progress.percentComplete if course_progress else 0,
            quizScorePercent=self.best_quiz_score_percent(user_id),
            labStatus=self.lab_status(user_id, course_id),  # type: ignore[arg-type]
        )

    def create_sandbox_session(
        self,
        user_id: str,
        course_id: str,
        lesson_id: str | None,
        runtime_limit_seconds: int,
        catalog: CourseCatalog,
        base_path: str,
    ) -> SandboxSession:
        course_id = course_id.upper()
        catalog.get_course(course_id, base_path)
        now = utc_now()
        audit = [SandboxAuditEvent(action="created", at=now, actorId=user_id)]
        session = SandboxSession(
            id=stable_id("sbx", user_id, course_id, lesson_id or "", now),
            courseId=course_id,
            lessonId=lesson_id,
            status="active",
            allowedTools=["python", "node", "http_mock"],
            runtimeLimitSeconds=max(30, min(runtime_limit_seconds, 900)),
            createdAt=now,
            auditTrail=audit,
        )
        self._sandbox_sessions[session.id] = {
            "user_id": user_id,
            "session": session,
        }
        self._flush()
        return session

    def evaluate_sandbox(
        self,
        user_id: str,
        session_id: str,
        artifact: str,
        rubric: list[str],
        sdk_task: dict[str, Any] | None = None,
    ) -> SandboxEvaluation:
        record = self._sandbox_sessions.get(session_id)
        if record is None:
            raise HTTPException(
                status_code=404, detail=f"Sandbox session not found: {session_id}"
            )
        if record["user_id"] != user_id:
            raise HTTPException(
                status_code=403, detail="Sandbox session belongs to another user."
            )

        session = record["session"]
        assert isinstance(session, SandboxSession)
        now = utc_now()
        adapter_result = (
            run_agent_sdk_lab_task(sdk_task, artifact, session.runtimeLimitSeconds)
            if sdk_task is not None
            and is_agent_sdk_lab_task(sdk_task)
            and self.sandbox_execution_enabled
            else None
        )
        run_result = (
            run_agent_artifact(artifact, session.runtimeLimitSeconds)
            if adapter_result is None and self.sandbox_execution_enabled
            else None
        )
        action = (
            "executed"
            if (adapter_result and adapter_result.executed)
            or (run_result and run_result.executed)
            else "evaluated"
        )
        audit = [
            *session.auditTrail,
            SandboxAuditEvent(action=action, at=now, actorId=user_id),
        ]
        score = self._static_artifact_score(artifact, rubric)
        execution_log: list[str] = []
        resource_usage: dict[str, int | str] = {}
        executed = False
        feedback = (
            "Static sandbox review completed without executing learner code. "
            "Runtime execution is intentionally disabled in the contract layer."
        )
        if run_result is not None:
            executed = run_result.executed
            execution_log = [
                line for line in [run_result.output, *run_result.errors] if line
            ]
            resource_usage = {"durationMs": run_result.durationMs}
            if run_result.executed and run_result.passed:
                score = min(100, max(score, 70))
                feedback = "Sandbox artifact executed successfully in the constrained training runner."
            elif run_result.executed:
                score = min(score, 55)
                feedback = (
                    "Sandbox artifact executed but did not complete successfully."
                )
            else:
                score = min(score, 40)
                feedback = "Sandbox artifact was rejected before execution by training runner guardrails."
        if adapter_result is not None:
            score = adapter_result.score
            executed = adapter_result.executed
            feedback = adapter_result.feedback
            execution_log = adapter_result.executionLog
            resource_usage = adapter_result.resourceUsage

        updated = session.model_copy(
            update={"status": "evaluated", "auditTrail": audit}
        )
        record["session"] = updated
        evaluation = SandboxEvaluation(
            sessionId=session_id,
            status="evaluated",
            score=score,
            passed=adapter_result.passed if adapter_result is not None else score >= 60,
            executed=executed,
            feedback=feedback,
            auditTrail=audit,
            executionLog=execution_log,
            resourceUsage=resource_usage,
            artifacts=adapter_result.artifacts if adapter_result is not None else [],
            rubricFeedback=[
                {
                    "id": item.id,
                    "passed": item.passed,
                    "pointsAwarded": item.pointsAwarded,
                    "pointsAvailable": item.pointsAvailable,
                    "feedback": item.feedback,
                }
                for item in (
                    adapter_result.rubricFeedback if adapter_result is not None else []
                )
            ],
            proofEligible=(
                adapter_result.proofEligible
                if adapter_result is not None
                else score >= 60
            ),
            adapter=adapter_result.adapter if adapter_result is not None else None,
        )
        self._sandbox_evaluations[session_id] = evaluation
        self._flush()
        return evaluation

    def _static_artifact_score(self, artifact: str, rubric: list[str]) -> int:
        normalized = artifact.strip()
        if not normalized:
            return 0
        score = 50
        if "return" in normalized:
            score += 20
        if "import requests" not in normalized and "http://" not in normalized:
            score += 15
        if rubric:
            score += min(15, len(rubric) * 5)
        return min(score, 100)
