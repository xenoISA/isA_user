"""Training service route registry for Consul metadata."""

from __future__ import annotations

from typing import Any

TRAINING_SERVICE_ROUTES = [
    {
        "path": "/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Health check",
    },
    {
        "path": "/api/v1/training/health",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Training API health check",
    },
    {
        "path": "/api/v1/training/courses",
        "methods": ["GET"],
        "auth_required": False,
        "description": "List course catalog sourced from isA_Training",
    },
    {
        "path": "/api/v1/training/courses/{course_id}",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get course detail sourced from isA_Training",
    },
    {
        "path": "/api/v1/training/enrollments",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Enroll current learner in a course",
    },
    {
        "path": "/api/v1/training/me/progress",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get current learner progress",
    },
    {
        "path": "/api/v1/training/me/timeline",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get current learner offline training timeline",
    },
    {
        "path": "/api/v1/training/lessons/complete",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Complete a lesson and update learner progress",
    },
    {
        "path": "/api/v1/training/quizzes/{quiz_id}",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Get quiz definition",
    },
    {
        "path": "/api/v1/training/quizzes/{quiz_id}/attempts",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create quiz attempt",
    },
    {
        "path": "/api/v1/training/attempts/{attempt_id}/submit",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Submit quiz attempt",
    },
    {
        "path": "/api/v1/training/sandbox/sessions",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create sandbox session",
    },
    {
        "path": "/api/v1/training/sandbox/sessions/{session_id}/evaluate",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Evaluate sandbox session",
    },
    {
        "path": "/api/v1/training/labs/{lab_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Get first-class lab definition",
    },
    {
        "path": "/api/v1/training/labs/{lab_id}/submissions",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Submit offline training lab artifact",
    },
    {
        "path": "/api/v1/training/completion-eligibility/{course_id}",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Check completion proof eligibility",
    },
    {
        "path": "/api/v1/training/completion-proofs",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Issue completion proof",
    },
    {
        "path": "/api/v1/training/completion-proofs/{proof_id_or_code}/verify",
        "methods": ["GET"],
        "auth_required": False,
        "description": "Verify completion proof",
    },
    {
        "path": "/api/v1/training/admin/cohorts",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Create organization cohort",
    },
    {
        "path": "/api/v1/training/admin/cohorts/{cohort_id}/enrollments",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Assign learners to offline cohort",
    },
    {
        "path": "/api/v1/training/admin/cohorts/{cohort_id}/attendance",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Record offline cohort attendance",
    },
    {
        "path": "/api/v1/training/admin/organizations/{organization_id}/dashboard",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Organization training dashboard",
    },
    {
        "path": "/api/v1/training/review/activity",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Operator review activity",
    },
    {
        "path": "/api/v1/training/review/queue",
        "methods": ["GET"],
        "auth_required": True,
        "description": "Review queue for tests and lab evaluations",
    },
    {
        "path": "/api/v1/training/review/items/{item_id}/override",
        "methods": ["POST"],
        "auth_required": True,
        "description": "Override reviewed test or lab evaluation",
    },
]


SERVICE_METADATA = {
    "service_name": "training_service",
    "port": 8262,
    "version": "0.1.0",
    "tags": ["v1", "user-microservice", "training", "learning"],
    "capabilities": [
        "course_catalog",
        "learner_progress",
        "quiz_scoring",
        "sandbox_evaluation",
        "completion_proofs",
        "cohort_reporting",
        "offline_attendance",
        "lab_contracts",
        "review_overrides",
    ],
    "health_check_path": "/health",
    "health_check_interval": "10s",
}


def get_routes_for_consul() -> dict[str, Any]:
    return {
        "route_count": str(len(TRAINING_SERVICE_ROUTES)),
        "base_path": "/api/v1/training",
        "methods": "GET,POST",
        "public_count": str(
            sum(1 for route in TRAINING_SERVICE_ROUTES if not route["auth_required"])
        ),
        "protected_count": str(
            sum(1 for route in TRAINING_SERVICE_ROUTES if route["auth_required"])
        ),
    }


def get_all_routes() -> list[dict[str, Any]]:
    return TRAINING_SERVICE_ROUTES
