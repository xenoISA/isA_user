"""API schemas for the training service."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AudienceLineCode = Literal["developer", "enterprise", "k12"]
AudienceLineStatus = Literal["available", "planned"]


class AudienceLine(BaseModel):
    code: AudienceLineCode
    name: str
    description: str
    status: AudienceLineStatus


class Track(BaseModel):
    code: str
    name: str


class Duration(BaseModel):
    hours: int
    minutes: int


class SourceAsset(BaseModel):
    path: str
    type: str
    available: bool
    status: Literal["available", "unavailable"]
    reason: str | None = None


class ManifestAsset(BaseModel):
    key: str
    value: str
    type: str


class AssetManifest(BaseModel):
    machineReadable: dict[str, str]
    humanAssets: list[ManifestAsset]


class Lesson(BaseModel):
    id: str
    lesson: str
    lessonType: str
    slideNumber: int
    duration: Duration
    sourceAsset: SourceAsset
    body: str
    notes: str


class Section(BaseModel):
    id: str
    section: str
    ordinal: int
    lessons: list[Lesson]


class CourseSummary(BaseModel):
    id: str
    course: str
    track: Track
    role: str
    supportedAudienceLines: list[AudienceLineCode]
    duration: Duration
    difficulty: str
    lessonType: str
    sourceAsset: SourceAsset
    slideCount: int | None = None
    notesCoverage: str | None = None
    sectionsUrl: str


class CourseDetail(CourseSummary):
    sections: list[Section]


class CoursePath(BaseModel):
    code: str
    name: str
    track: Track
    courseCount: int
    duration: Duration
    courses: list[CourseSummary]


class CourseList(BaseModel):
    platform: str
    totalCourses: int
    totalHours: int
    audienceLines: list[AudienceLine]
    paths: list[CoursePath]
    assetManifest: AssetManifest


class EnrollmentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    courseId: str = Field(alias="course_id")


class Enrollment(BaseModel):
    id: str
    courseId: str
    status: Literal["active", "completed", "paused"]
    startedAt: str
    completedAt: str | None = None
    lastActivityAt: str


class ActiveCourseProgress(BaseModel):
    courseId: str
    enrollmentId: str
    status: str
    completedLessonCount: int
    totalLessonCount: int
    nextLessonId: str | None = None


class LessonProgress(BaseModel):
    completedLessons: list[str]
    totalLessons: int
    percentComplete: int
    resumeLessonId: str | None = None
    lastActivityAt: str | None = None
    activityEvents: list["LessonActivityEvent"] = Field(default_factory=list)


class TrainingProgress(BaseModel):
    enrollments: list[Enrollment]
    activeCourses: list[ActiveCourseProgress]
    lessonProgress: dict[str, LessonProgress]
    quizState: dict[str, Any]
    completionPercent: int


class SubmissionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    courseId: str = Field(alias="course_id")
    lessonId: str = Field(alias="lesson_id")
    content: str


class Submission(BaseModel):
    id: str
    courseId: str
    lessonId: str
    status: Literal["queued", "submitted", "evaluated", "rejected"]
    score: int
    feedback: str
    submittedAt: str


class LessonActivityRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    courseId: str = Field(alias="course_id")
    lessonId: str = Field(alias="lesson_id")
    activityType: Literal[
        "asset_viewed",
        "checkpoint_started",
        "checkpoint_completed",
        "lesson_completed",
        "resume_position",
    ] = Field(alias="activity_type")
    positionSeconds: int | None = Field(default=None, alias="position_seconds")
    assetKey: str | None = Field(default=None, alias="asset_key")
    required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class LessonActivityEvent(BaseModel):
    id: str
    learnerId: str
    courseId: str
    lessonId: str
    activityType: str
    positionSeconds: int | None = None
    assetKey: str | None = None
    required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    createdAt: str


QuestionType = Literal["single_choice", "multiple_choice", "short_answer"]


class Question(BaseModel):
    id: str
    module: str
    knowledge: str
    difficulty: str
    type: QuestionType
    stem: str
    options: dict[str, str]
    tags: list[str]
    sourceLessonId: str


class Quiz(BaseModel):
    id: str
    title: str
    questionCount: int
    questions: list[Question]
    scenario: Literal["entry", "module", "final", "practice"] = "practice"
    variant: str = "A"


class QuizAttempt(BaseModel):
    id: str
    quizId: str
    status: Literal["in_progress", "submitted", "evaluated"]
    questionIds: list[str]
    startedAt: str
    submittedAt: str | None = None
    scenario: Literal["entry", "module", "final", "practice"] = "practice"
    variant: str = "A"


class QuizSubmitRequest(BaseModel):
    answers: dict[str, str | list[str]]


class QuestionReview(BaseModel):
    questionId: str
    correct: bool
    answer: str | list[str] | None = None
    correctAnswer: str | list[str] | None = None
    explanation: str


class QuizResult(BaseModel):
    attemptId: str
    quizId: str
    status: Literal["evaluated"]
    score: int
    total: int
    correct: int
    reviews: list[QuestionReview]
    submittedAt: str


class AssistantChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str
    courseId: str = Field(alias="course_id")
    lessonId: str | None = Field(default=None, alias="lesson_id")


class AssistantCitation(BaseModel):
    courseId: str
    sectionId: str
    lessonId: str
    sourceAsset: SourceAsset
    excerpt: str
    sourceId: str
    score: int


class AssistantChatResponse(BaseModel):
    status: Literal["answered", "fallback"]
    answer: str
    citations: list[AssistantCitation]
    fallbackReason: str | None = None


class SandboxSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    courseId: str = Field(alias="course_id")
    lessonId: str | None = Field(default=None, alias="lesson_id")
    runtimeLimitSeconds: int = Field(default=300, alias="runtime_limit_seconds")


class SandboxAuditEvent(BaseModel):
    action: str
    at: str
    actorId: str


class SandboxSession(BaseModel):
    id: str
    courseId: str
    lessonId: str | None = None
    status: Literal["active", "evaluated", "closed"]
    allowedTools: list[str]
    runtimeLimitSeconds: int
    createdAt: str
    auditTrail: list[SandboxAuditEvent]


class SandboxEvaluationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    artifact: str
    rubric: list[str] = Field(default_factory=list)
    sdkTask: dict[str, Any] | None = Field(default=None, alias="sdk_task")


class LabDefinition(BaseModel):
    id: str
    title: str
    courseId: str
    lessonId: str | None = None
    setup: list[dict[str, Any]] = Field(default_factory=list)
    task: dict[str, Any] = Field(default_factory=dict)
    rubric: list[dict[str, Any]] = Field(default_factory=list)
    artifactSchema: dict[str, Any] = Field(default_factory=dict)
    resourceLimits: dict[str, int | str] = Field(default_factory=dict)
    passingScore: int
    proofEligible: bool = False


class LabSubmissionRequest(BaseModel):
    artifact: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SandboxEvaluation(BaseModel):
    sessionId: str
    status: Literal["evaluated"]
    score: int
    passed: bool
    executed: bool
    feedback: str
    auditTrail: list[SandboxAuditEvent]
    executionLog: list[str] = Field(default_factory=list)
    resourceUsage: dict[str, int | str] = Field(default_factory=dict)
    artifacts: list[dict[str, str]] = Field(default_factory=list)
    rubricFeedback: list[dict[str, int | str | bool]] = Field(default_factory=list)
    proofEligible: bool = False
    adapter: str | None = None


class LabSubmissionResult(SandboxEvaluation):
    submissionId: str
    labId: str
    learnerId: str
    courseId: str
    reviewStatus: Literal[
        "pending_review", "approved", "rejected", "resubmission_requested"
    ]


class CompletionProofRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    courseId: str = Field(alias="course_id")


class CompletionProofVerification(BaseModel):
    status: Literal["verifiable"]
    code: str
    method: str


class CompletionProof(BaseModel):
    id: str
    type: Literal["completion_proof"]
    learnerId: str
    courseId: str
    issuedAt: str
    progressPercent: int
    quizScorePercent: int
    labStatus: Literal["passed", "missing"]
    verification: CompletionProofVerification


class CompletionProofVerificationResponse(BaseModel):
    proofId: str
    courseId: str
    status: Literal["valid", "not_found"]
    verificationCode: str | None = None
    issuedAt: str | None = None
    proofType: Literal["completion_proof"] | None = None


class CompletionEligibilityResponse(BaseModel):
    eligible: bool
    missing: list[str]
    progressPercent: int
    quizScorePercent: int
    labStatus: Literal["passed", "missing"]
    attendanceStatus: Literal["present", "missing", "not_required"]


class PathRecommendationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    attemptId: str = Field(alias="attempt_id")
    role: str = "developer"


class PathRecommendation(BaseModel):
    id: str
    learnerId: str
    role: str
    attemptId: str
    recommendedPathCode: str
    startCourseId: str
    skippedCourseIds: list[str]
    reinforcementCourseIds: list[str]
    dimensionScores: dict[str, int]
    rationale: list[str]
    createdAt: str


class RolePolicy(BaseModel):
    create: list[str]
    read: list[str]
    review: list[str]


class CohortRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    organizationId: str = Field(alias="organization_id")
    name: str
    pathCode: str = Field(alias="path_code")
    courseIds: list[str] = Field(alias="course_ids")
    learnerIds: list[str] = Field(alias="learner_ids")
    startAt: str | None = Field(default=None, alias="start_at")
    endAt: str | None = Field(default=None, alias="end_at")
    deliveryStatus: Literal[
        "scheduled", "in_progress", "completed", "cancelled"
    ] = Field(
        default="scheduled",
        alias="delivery_status",
    )


class CohortEnrollmentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    learnerIds: list[str] = Field(alias="learner_ids")


class AttendanceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    learnerId: str = Field(alias="learner_id")
    courseId: str = Field(alias="course_id")
    status: Literal["present", "absent", "excused"]
    metadata: dict[str, Any] = Field(default_factory=dict)


class Cohort(BaseModel):
    id: str
    organizationId: str
    name: str
    pathCode: str
    courseIds: list[str]
    learnerIds: list[str]
    createdAt: str
    startAt: str | None = None
    endAt: str | None = None
    deliveryStatus: Literal[
        "scheduled", "in_progress", "completed", "cancelled"
    ] = "scheduled"
    rolePolicy: RolePolicy


class TrainingTimelineEvent(BaseModel):
    id: str
    learnerId: str
    eventType: str
    source: str
    actorId: str
    createdAt: str
    courseId: str | None = None
    cohortId: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrainingTimeline(BaseModel):
    events: list[TrainingTimelineEvent]


class ReviewOverrideRequest(BaseModel):
    status: Literal["approved", "rejected", "resubmission_requested"]
    score: int | None = None
    passed: bool | None = None
    reason: str


class ReviewQueueItem(BaseModel):
    id: str
    sourceType: str
    learnerId: str
    courseId: str | None = None
    labId: str | None = None
    status: str
    score: int | None = None
    passed: bool | None = None
    createdAt: str
    finalStatus: str | None = None
    overrideReason: str | None = None


class ReviewQueue(BaseModel):
    items: list[ReviewQueueItem]


class LearnerCourseSummary(BaseModel):
    learnerId: str
    courseId: str
    progressPercent: int
    quizScorePercent: int | None = None
    labStatus: Literal["passed", "missing"]


class CohortDashboard(BaseModel):
    cohortId: str
    name: str
    completionPercent: int
    learners: list[LearnerCourseSummary]


class OrganizationDashboard(BaseModel):
    organizationId: str
    featureFlag: str
    cohorts: list[CohortDashboard]


class OrganizationReport(BaseModel):
    organizationId: str
    format: Literal["csv"]
    columns: list[str]
    rows: list[dict[str, str | int | None]]


class CourseLearnerReview(BaseModel):
    courseId: str
    learners: list[LearnerCourseSummary]


class ReviewActivity(BaseModel):
    quizAttempts: list[dict[str, Any]]
    labSubmissions: list[dict[str, Any]]
    flaggedAssistantSessions: list[dict[str, Any]]
