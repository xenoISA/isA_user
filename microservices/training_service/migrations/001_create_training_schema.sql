-- Training Service operational schema.
-- Source content remains in isA_Training; these tables store learner/runtime state.

CREATE SCHEMA IF NOT EXISTS training;

CREATE TABLE IF NOT EXISTS training.state_snapshots (
    store_kind TEXT PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training.enrollments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NULL,
    last_activity_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, course_id)
);

CREATE TABLE IF NOT EXISTS training.lesson_progress (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL,
    submission_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, course_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS training.lesson_activity_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    position_seconds INTEGER,
    asset_key TEXT,
    required BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS training.timeline_events (
    id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    course_id TEXT,
    cohort_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS training.submissions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    content TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS training.quiz_attempts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    quiz_id TEXT NOT NULL,
    scenario TEXT,
    variant TEXT,
    status TEXT NOT NULL,
    question_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    answers JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    started_at TIMESTAMPTZ NOT NULL,
    submitted_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS training.sandbox_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    status TEXT NOT NULL,
    runtime_limit_seconds INTEGER NOT NULL,
    audit_trail JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS training.sandbox_evaluations (
    session_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    score INTEGER NOT NULL,
    passed BOOLEAN NOT NULL,
    executed BOOLEAN NOT NULL,
    feedback TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training.lab_submissions (
    id TEXT PRIMARY KEY,
    lab_id TEXT NOT NULL,
    learner_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    score INTEGER NOT NULL,
    passed BOOLEAN NOT NULL,
    proof_eligible BOOLEAN NOT NULL DEFAULT FALSE,
    review_status TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS training.review_records (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    learner_id TEXT NOT NULL,
    course_id TEXT,
    lab_id TEXT,
    status TEXT NOT NULL,
    score INTEGER,
    passed BOOLEAN,
    final_status TEXT,
    override_reason TEXT,
    override_actor_id TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    overridden_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS training.completion_proofs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    proof_type TEXT NOT NULL,
    verification_code TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    issued_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS training.cohorts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    name TEXT NOT NULL,
    path_code TEXT NOT NULL,
    course_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    learner_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    delivery_status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS training.assistant_interactions (
    id BIGSERIAL PRIMARY KEY,
    request_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    course_id TEXT NOT NULL,
    lesson_id TEXT,
    status TEXT NOT NULL,
    citation_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_enrollments_user_id
    ON training.enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_training_lesson_progress_user_course
    ON training.lesson_progress(user_id, course_id);
CREATE INDEX IF NOT EXISTS idx_training_lesson_activity_user_course
    ON training.lesson_activity_events(user_id, course_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_training_timeline_learner
    ON training.timeline_events(learner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_training_lab_submissions_learner_course
    ON training.lab_submissions(learner_id, course_id);
CREATE INDEX IF NOT EXISTS idx_training_review_records_status
    ON training.review_records(status, final_status);
CREATE INDEX IF NOT EXISTS idx_training_quiz_attempts_user_id
    ON training.quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_training_cohorts_organization_id
    ON training.cohorts(organization_id);
CREATE INDEX IF NOT EXISTS idx_training_completion_proofs_user_id
    ON training.completion_proofs(user_id);
