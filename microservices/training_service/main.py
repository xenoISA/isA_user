"""ASGI entrypoint for the isA user training microservice."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is a runtime dependency.
    load_dotenv = None

from .assistant import CourseAssistant
from .auth import require_any_role, require_organization_role, require_user_id
from .catalog import CourseCatalog, CourseNotFound
from .config import Settings, get_settings
from .k12 import load_k12_contract
from .learning import TrainingStateStore
from .observability import TrainingObservability, request_id_from_headers
from .persistence import PostgresTrainingPersistence
from .questions import QuestionBank
from .schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AudienceLineCode,
    AttendanceRequest,
    Cohort,
    CohortEnrollmentRequest,
    CohortRequest,
    CompletionEligibilityResponse,
    CompletionProof,
    CompletionProofRequest,
    CompletionProofVerificationResponse,
    CourseDetail,
    CourseLearnerReview,
    CourseList,
    Enrollment,
    EnrollmentRequest,
    LabDefinition,
    LabSubmissionRequest,
    LabSubmissionResult,
    LessonActivityEvent,
    LessonActivityRequest,
    OrganizationDashboard,
    OrganizationReport,
    PathRecommendation,
    PathRecommendationRequest,
    Quiz,
    QuizAttempt,
    QuizResult,
    QuizSubmitRequest,
    ReviewActivity,
    ReviewOverrideRequest,
    ReviewQueue,
    ReviewQueueItem,
    SandboxEvaluation,
    SandboxEvaluationRequest,
    SandboxSession,
    SandboxSessionRequest,
    Submission,
    SubmissionRequest,
    TrainingTimeline,
    TrainingTimelineEvent,
    TrainingProgress,
)
from .service_discovery import create_service_registration

logger = logging.getLogger(__name__)


def _load_env() -> None:
    if load_dotenv is None:
        return

    project_root = Path(__file__).resolve().parents[2]
    load_dotenv()
    load_dotenv(project_root / "deployment" / "environments" / "dev.env")


def service_health(settings: Settings) -> dict[str, Any]:
    """Return the shared health payload for root and versioned endpoints."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "environment": settings.environment,
        "base_path": settings.base_path,
        "checks": {"app": "ok"},
    }


def create_state_store(settings: Settings) -> TrainingStateStore:
    """Create the training state store from service persistence settings."""
    backend = settings.training_persistence_backend
    if backend == "postgres":
        return TrainingStateStore(
            persistence=PostgresTrainingPersistence(settings.training_database_url),
            sandbox_execution_enabled=settings.sandbox_execution_enabled,
        )
    if backend == "json" and settings.training_state_path is not None:
        return TrainingStateStore(
            storage_path=settings.training_state_path,
            sandbox_execution_enabled=settings.sandbox_execution_enabled,
        )
    if backend not in {"memory", "json"}:
        raise ValueError(f"Unsupported training persistence backend: {backend}")
    return TrainingStateStore(
        sandbox_execution_enabled=settings.sandbox_execution_enabled,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    registration = None
    logger.info(
        "Starting %s (env=%s, port=%s)",
        settings.service_name,
        settings.environment,
        settings.service_port,
    )
    try:
        registration = create_service_registration(settings)
        app.state.service_registration = registration
        if registration is not None:
            registration.register()
    except Exception:
        registration = None
        app.state.service_registration = None
        logger.exception("Training service discovery registration failed")

    try:
        yield
    finally:
        if registration is not None:
            try:
                registration.deregister()
            except Exception:
                logger.exception("Training service discovery deregistration failed")
    logger.info("Shutting down %s", settings.service_name)


def create_app(
    settings: Settings | None = None,
    catalog: CourseCatalog | None = None,
    state_store: TrainingStateStore | None = None,
    question_bank: QuestionBank | None = None,
    course_assistant: CourseAssistant | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application."""
    _load_env()
    settings = settings or get_settings()
    catalog = catalog or CourseCatalog()
    state_store = state_store or create_state_store(settings)
    question_bank = question_bank or QuestionBank(catalog.data_root)
    course_assistant = course_assistant or CourseAssistant()
    observability = TrainingObservability()

    app = FastAPI(
        title="isA Training Service",
        description="Operational training runtime for the isA user platform",
        version=settings.version,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.catalog = catalog
    app.state.training_state = state_store
    app.state.question_bank = question_bank
    app.state.course_assistant = course_assistant
    app.state.observability = observability

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def attach_request_observability(request: Request, call_next):
        request_id = request_id_from_headers(request.headers)
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000)
        response.headers["x-request-id"] = request_id
        observability.record_http_request(
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        logger.info(
            "training_request method=%s path=%s status=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, Any]:
        return service_health(settings)

    @app.get(f"{settings.base_path}/health", tags=["health"])
    async def api_health() -> dict[str, Any]:
        return service_health(settings)

    @app.get(
        f"{settings.base_path}/observability/metrics",
        response_class=PlainTextResponse,
        tags=["observability"],
    )
    async def training_metrics() -> Response:
        return PlainTextResponse(
            observability.render_prometheus(),
            media_type="text/plain; version=0.0.4",
        )

    @app.get("/live", tags=["health"])
    async def live() -> dict[str, str]:
        return {"status": "alive", "service": settings.service_name}

    @app.get(
        f"{settings.base_path}/courses",
        response_model=CourseList,
        tags=["catalog"],
    )
    async def list_courses(
        audience_line: AudienceLineCode
        | None = Query(
            default=None,
            description="Optional audience line filter: developer, enterprise, or k12.",
        ),
    ) -> CourseList:
        return catalog.list_courses(settings.base_path, audience_line=audience_line)

    @app.get(
        f"{settings.base_path}/courses/{{course_id}}",
        response_model=CourseDetail,
        tags=["catalog"],
    )
    async def get_course(course_id: str) -> CourseDetail:
        try:
            return catalog.get_course(course_id, settings.base_path)
        except CourseNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        f"{settings.base_path}/enrollments",
        response_model=Enrollment,
        status_code=status.HTTP_201_CREATED,
        tags=["learning"],
    )
    async def enroll_course(
        payload: EnrollmentRequest,
        request: Request,
    ) -> Enrollment:
        user_id = require_user_id(request)
        try:
            return state_store.enroll(
                user_id=user_id,
                course_id=payload.courseId,
                catalog=catalog,
                base_path=settings.base_path,
            )
        except CourseNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        f"{settings.base_path}/me/progress",
        response_model=TrainingProgress,
        tags=["learning"],
    )
    async def get_my_progress(request: Request) -> TrainingProgress:
        user_id = require_user_id(request)
        return state_store.progress(user_id, catalog, settings.base_path)

    @app.get(
        f"{settings.base_path}/me/timeline",
        response_model=TrainingTimeline,
        tags=["learning"],
    )
    async def get_my_timeline(request: Request) -> TrainingTimeline:
        user_id = require_user_id(request)
        return TrainingTimeline(events=state_store.timeline_for_learner(user_id))

    @app.post(
        f"{settings.base_path}/submissions",
        response_model=Submission,
        status_code=status.HTTP_201_CREATED,
        tags=["learning"],
    )
    async def submit_work(
        payload: SubmissionRequest,
        request: Request,
    ) -> Submission:
        user_id = require_user_id(request)
        try:
            return state_store.submit_work(
                user_id=user_id,
                course_id=payload.courseId,
                lesson_id=payload.lessonId,
                content=payload.content,
                catalog=catalog,
                base_path=settings.base_path,
            )
        except CourseNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        f"{settings.base_path}/lessons/complete",
        response_model=Submission,
        status_code=status.HTTP_201_CREATED,
        tags=["learning"],
    )
    async def complete_lesson(
        payload: SubmissionRequest,
        request: Request,
    ) -> Submission:
        return await submit_work(payload, request)

    @app.post(
        f"{settings.base_path}/lessons/activity",
        response_model=LessonActivityEvent,
        status_code=status.HTTP_201_CREATED,
        tags=["learning"],
    )
    async def record_lesson_activity(
        payload: LessonActivityRequest,
        request: Request,
    ) -> LessonActivityEvent:
        user_id = require_user_id(request)
        try:
            return state_store.record_lesson_activity(
                user_id=user_id,
                course_id=payload.courseId,
                lesson_id=payload.lessonId,
                activity_type=payload.activityType,
                position_seconds=payload.positionSeconds,
                asset_key=payload.assetKey,
                required=payload.required,
                metadata=payload.metadata,
                catalog=catalog,
                base_path=settings.base_path,
            )
        except CourseNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        f"{settings.base_path}/quizzes/{{quiz_id}}",
        response_model=Quiz,
        tags=["assessment"],
    )
    async def get_quiz(quiz_id: str) -> Quiz:
        return question_bank.get_quiz(quiz_id)

    @app.post(
        f"{settings.base_path}/quizzes/{{quiz_id}}/attempts",
        response_model=QuizAttempt,
        status_code=status.HTTP_201_CREATED,
        tags=["assessment"],
    )
    async def create_quiz_attempt(quiz_id: str, request: Request) -> QuizAttempt:
        user_id = require_user_id(request)
        question_ids = question_bank.question_ids(quiz_id)
        scenario = question_bank.scenario_for_quiz(quiz_id)
        attempt = state_store.create_quiz_attempt(
            user_id,
            quiz_id,
            question_ids,
            scenario=scenario,
            variant="A",
        )
        return QuizAttempt(
            id=str(attempt["id"]),
            quizId=str(attempt["quiz_id"]),
            status="in_progress",
            questionIds=[str(item) for item in attempt["question_ids"]],
            startedAt=str(attempt["started_at"]),
            submittedAt=None,
            scenario=scenario,  # type: ignore[arg-type]
            variant="A",
        )

    @app.post(
        f"{settings.base_path}/attempts/{{attempt_id}}/submit",
        response_model=QuizResult,
        tags=["assessment"],
    )
    async def submit_quiz_attempt(
        attempt_id: str,
        payload: QuizSubmitRequest,
        request: Request,
    ) -> QuizResult:
        user_id = require_user_id(request)
        attempt = state_store.get_owned_quiz_attempt(user_id, attempt_id)
        submitted_at = state_store.update_quiz_attempt(attempt_id, payload.answers)
        result = question_bank.score_attempt(
            quiz_id=str(attempt["quiz_id"]),
            attempt_id=attempt_id,
            answers=payload.answers,
            submitted_at=submitted_at,
        )
        state_store.record_quiz_result(
            attempt_id=attempt_id,
            score=result.score,
            total=result.total,
            correct=result.correct,
            reviews=[review.model_dump(mode="json") for review in result.reviews],
        )
        return result

    @app.post(
        f"{settings.base_path}/path-recommendations",
        response_model=PathRecommendation,
        status_code=status.HTTP_201_CREATED,
        tags=["assessment"],
    )
    async def create_path_recommendation(
        payload: PathRecommendationRequest,
        request: Request,
    ) -> PathRecommendation:
        user_id = require_user_id(request)
        return state_store.path_recommendation(
            user_id=user_id,
            attempt_id=payload.attemptId,
            role=payload.role,
        )

    @app.post(
        f"{settings.base_path}/assistant/chat",
        response_model=AssistantChatResponse,
        tags=["assistant"],
    )
    async def assistant_chat(
        payload: AssistantChatRequest,
        request: Request,
    ) -> AssistantChatResponse:
        user_id = require_user_id(request)
        try:
            response = course_assistant.answer(
                catalog=catalog,
                base_path=settings.base_path,
                course_id=payload.courseId,
                lesson_id=payload.lessonId,
                question=payload.question,
            )
            observability.record_assistant_response(
                status=response.status,
                citation_count=len(response.citations),
            )
            state_store.record_assistant_interaction(
                user_id=user_id,
                course_id=payload.courseId,
                lesson_id=payload.lessonId,
                status=response.status,
                citation_count=len(response.citations),
                request_id=getattr(request.state, "request_id", "training-local"),
            )
            return response
        except CourseNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        f"{settings.base_path}/sandbox/sessions",
        response_model=SandboxSession,
        status_code=status.HTTP_201_CREATED,
        tags=["sandbox"],
    )
    async def create_sandbox_session(
        payload: SandboxSessionRequest,
        request: Request,
    ) -> SandboxSession:
        user_id = require_user_id(request)
        try:
            return state_store.create_sandbox_session(
                user_id=user_id,
                course_id=payload.courseId,
                lesson_id=payload.lessonId,
                runtime_limit_seconds=payload.runtimeLimitSeconds,
                catalog=catalog,
                base_path=settings.base_path,
            )
        except CourseNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        f"{settings.base_path}/sandbox/sessions/{{session_id}}/evaluate",
        response_model=SandboxEvaluation,
        tags=["sandbox"],
    )
    async def evaluate_sandbox_session(
        session_id: str,
        payload: SandboxEvaluationRequest,
        request: Request,
    ) -> SandboxEvaluation:
        user_id = require_user_id(request)
        evaluation = state_store.evaluate_sandbox(
            user_id=user_id,
            session_id=session_id,
            artifact=payload.artifact,
            rubric=payload.rubric,
            sdk_task=payload.sdkTask,
        )
        observability.record_sandbox_evaluation(
            executed=evaluation.executed,
            passed=evaluation.passed,
        )
        return evaluation

    @app.get(
        f"{settings.base_path}/labs/{{lab_id}}",
        response_model=LabDefinition,
        tags=["sandbox"],
    )
    async def get_lab(lab_id: str) -> LabDefinition:
        return state_store.lab_definition(lab_id)

    @app.post(
        f"{settings.base_path}/labs/{{lab_id}}/submissions",
        response_model=LabSubmissionResult,
        status_code=status.HTTP_201_CREATED,
        tags=["sandbox"],
    )
    async def submit_lab(
        lab_id: str,
        payload: LabSubmissionRequest,
        request: Request,
    ) -> LabSubmissionResult:
        user_id = require_user_id(request)
        return state_store.submit_lab(
            lab_id=lab_id,
            learner_id=user_id,
            artifact=payload.artifact,
            metadata=payload.metadata,
        )

    @app.get(
        f"{settings.base_path}/completion-eligibility/{{course_id}}",
        response_model=CompletionEligibilityResponse,
        tags=["completion"],
    )
    async def completion_eligibility(
        course_id: str,
        request: Request,
    ) -> CompletionEligibilityResponse:
        user_id = require_user_id(request)
        return CompletionEligibilityResponse(
            **state_store.completion_eligibility(
                user_id=user_id,
                course_id=course_id,
                catalog=catalog,
                base_path=settings.base_path,
            )
        )

    @app.post(
        f"{settings.base_path}/completion-proofs",
        response_model=CompletionProof,
        status_code=status.HTTP_201_CREATED,
        tags=["completion"],
    )
    async def create_completion_proof(
        payload: CompletionProofRequest,
        request: Request,
    ) -> CompletionProof:
        user_id = require_user_id(request)
        try:
            return state_store.completion_proof(
                user_id=user_id,
                course_id=payload.courseId,
                catalog=catalog,
                base_path=settings.base_path,
            )
        except CourseNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        f"{settings.base_path}/completion-proofs/{{proof_id_or_code}}/verify",
        response_model=CompletionProofVerificationResponse,
        tags=["completion"],
    )
    async def verify_completion_proof(
        proof_id_or_code: str,
    ) -> CompletionProofVerificationResponse:
        proof = state_store.verify_completion_proof(proof_id_or_code)
        if proof is None:
            observability.record_completion_proof_verification("not_found")
            return CompletionProofVerificationResponse(
                proofId=proof_id_or_code,
                courseId="",
                status="not_found",
            )
        observability.record_completion_proof_verification("valid")
        return CompletionProofVerificationResponse(
            proofId=proof.id,
            courseId=proof.courseId,
            status="valid",
            verificationCode=proof.verification.code,
            issuedAt=proof.issuedAt,
            proofType=proof.type,
        )

    @app.post(
        f"{settings.base_path}/admin/cohorts",
        response_model=Cohort,
        status_code=status.HTTP_201_CREATED,
        tags=["enterprise"],
    )
    async def create_cohort(
        payload: CohortRequest,
        request: Request,
    ) -> Cohort:
        require_organization_role(
            request, payload.organizationId, {"org_admin", "operator"}
        )
        return state_store.create_cohort(
            organization_id=payload.organizationId,
            name=payload.name,
            path_code=payload.pathCode,
            course_ids=payload.courseIds,
            learner_ids=payload.learnerIds,
            start_at=payload.startAt,
            end_at=payload.endAt,
            delivery_status=payload.deliveryStatus,
        )

    @app.post(
        f"{settings.base_path}/admin/cohorts/{{cohort_id}}/enrollments",
        response_model=Cohort,
        tags=["enterprise"],
    )
    async def assign_cohort_learners(
        cohort_id: str,
        payload: CohortEnrollmentRequest,
        request: Request,
    ) -> Cohort:
        require_any_role(request, {"org_admin", "operator"})
        actor_id = require_user_id(request)
        return state_store.assign_learners_to_cohort(
            cohort_id=cohort_id,
            learner_ids=payload.learnerIds,
            actor_id=actor_id,
        )

    @app.post(
        f"{settings.base_path}/admin/cohorts/{{cohort_id}}/attendance",
        response_model=TrainingTimelineEvent,
        status_code=status.HTTP_201_CREATED,
        tags=["enterprise"],
    )
    async def mark_attendance(
        cohort_id: str,
        payload: AttendanceRequest,
        request: Request,
    ) -> TrainingTimelineEvent:
        require_any_role(request, {"org_admin", "operator", "teacher"})
        actor_id = require_user_id(request)
        return state_store.record_attendance(
            cohort_id=cohort_id,
            learner_id=payload.learnerId,
            course_id=payload.courseId,
            attendance_status=payload.status,
            actor_id=actor_id,
            metadata=payload.metadata,
        )

    @app.get(
        f"{settings.base_path}/admin/organizations/{{organization_id}}/dashboard",
        response_model=OrganizationDashboard,
        tags=["enterprise"],
    )
    async def organization_dashboard(
        organization_id: str,
        request: Request,
    ) -> OrganizationDashboard:
        require_organization_role(request, organization_id, {"org_admin", "operator"})
        return state_store.organization_dashboard(
            organization_id=organization_id,
            catalog=catalog,
            base_path=settings.base_path,
        )

    @app.get(
        f"{settings.base_path}/admin/organizations/{{organization_id}}/report",
        response_model=OrganizationReport,
        tags=["enterprise"],
    )
    async def organization_report(
        organization_id: str,
        request: Request,
    ) -> OrganizationReport:
        require_organization_role(request, organization_id, {"org_admin", "operator"})
        return state_store.organization_report(
            organization_id=organization_id,
            catalog=catalog,
            base_path=settings.base_path,
        )

    @app.get(
        f"{settings.base_path}/review/courses/{{course_id}}/learners",
        response_model=CourseLearnerReview,
        tags=["review"],
    )
    async def review_course_learners(
        course_id: str,
        request: Request,
    ) -> CourseLearnerReview:
        require_any_role(request, {"teacher", "operator", "org_admin"})
        return CourseLearnerReview(
            courseId=course_id.upper(),
            learners=state_store.course_learners(
                course_id=course_id,
                catalog=catalog,
                base_path=settings.base_path,
            ),
        )

    @app.get(
        f"{settings.base_path}/review/activity",
        response_model=ReviewActivity,
        tags=["review"],
    )
    async def review_activity(request: Request) -> ReviewActivity:
        require_any_role(request, {"operator", "org_admin"})
        return ReviewActivity(**state_store.review_activity())

    @app.get(
        f"{settings.base_path}/review/queue",
        response_model=ReviewQueue,
        tags=["review"],
    )
    async def review_queue(request: Request) -> ReviewQueue:
        require_any_role(request, {"teacher", "operator", "org_admin"})
        return ReviewQueue(
            items=[ReviewQueueItem(**item) for item in state_store.review_queue()]
        )

    @app.post(
        f"{settings.base_path}/review/items/{{item_id}}/override",
        response_model=ReviewQueueItem,
        tags=["review"],
    )
    async def override_review_item(
        item_id: str,
        payload: ReviewOverrideRequest,
        request: Request,
    ) -> ReviewQueueItem:
        require_any_role(request, {"teacher", "operator", "org_admin"})
        actor_id = require_user_id(request)
        return ReviewQueueItem(
            **state_store.override_review_item(
                item_id=item_id,
                final_status=payload.status,
                score=payload.score,
                passed=payload.passed,
                reason=payload.reason,
                actor_id=actor_id,
            )
        )

    @app.get(
        f"{settings.base_path}/k12/contract",
        tags=["k12"],
    )
    async def k12_contract() -> dict[str, Any]:
        return load_k12_contract()

    return app


app = create_app()


def run() -> None:
    """Run the development server."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "microservices.training_service.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.environment == "development",
    )
