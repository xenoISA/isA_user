import json
from pathlib import Path

from fastapi.testclient import TestClient

from microservices.training_service.catalog import CourseCatalog
from microservices.training_service.config import Settings
from microservices.training_service.learning import TrainingStateStore
from microservices.training_service.main import create_app
from microservices.training_service.persistence import JsonFileTrainingPersistence
from microservices.training_service.routes_registry import (
    SERVICE_METADATA,
    get_all_routes,
    get_routes_for_consul,
)

FIXTURE_DATA_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "training_data"


def _settings(**overrides):
    values = {
        "service_name": "training_service",
        "service_port": 8262,
        "environment": "test",
        "version": "0.1.0",
        "sandbox_execution_enabled": False,
    }
    values.update(overrides)
    return Settings(**values)


def _client(
    *,
    settings: Settings | None = None,
    state_store: TrainingStateStore | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            settings=settings or _settings(),
            catalog=CourseCatalog(FIXTURE_DATA_ROOT),
            state_store=state_store,
        )
    )


def test_training_service_loads_course_catalog_from_training_content_source():
    client = _client()

    response = client.get("/api/v1/training/courses")

    assert response.status_code == 200
    payload = response.json()
    assert payload["platform"] == "isA_Training"
    assert payload["totalCourses"] >= 18


def test_training_state_round_trips_through_persistence_backend(tmp_path):
    state_path = tmp_path / "training-state.json"
    first = TestClient(
        create_app(
            settings=_settings(),
            catalog=CourseCatalog(FIXTURE_DATA_ROOT),
            state_store=TrainingStateStore(
                persistence=JsonFileTrainingPersistence(state_path),
                sandbox_execution_enabled=False,
            ),
        )
    )

    headers = {"x-user-id": "learner-a"}
    enrolled = first.post(
        "/api/v1/training/enrollments",
        headers=headers,
        json={"course_id": "F1"},
    )
    assert enrolled.status_code == 201

    second = TestClient(
        create_app(
            settings=_settings(),
            catalog=CourseCatalog(FIXTURE_DATA_ROOT),
            state_store=TrainingStateStore(
                persistence=JsonFileTrainingPersistence(state_path),
                sandbox_execution_enabled=False,
            ),
        )
    )
    progress = second.get("/api/v1/training/me/progress", headers=headers)

    assert progress.status_code == 200
    assert progress.json()["enrollments"][0]["courseId"] == "F1"
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["storeKind"] == "training_service_operational_state"


def test_lesson_activity_events_update_resume_state_and_persist(tmp_path):
    state_path = tmp_path / "training-state.json"
    headers = {"x-user-id": "learner-a"}
    first = TestClient(
        create_app(
            settings=_settings(),
            catalog=CourseCatalog(FIXTURE_DATA_ROOT),
            state_store=TrainingStateStore(
                persistence=JsonFileTrainingPersistence(state_path),
                sandbox_execution_enabled=False,
            ),
        )
    )
    first.post(
        "/api/v1/training/enrollments", headers=headers, json={"course_id": "F1"}
    )

    event = first.post(
        "/api/v1/training/lessons/activity",
        headers=headers,
        json={
            "course_id": "F1",
            "lesson_id": "F1-L2",
            "activity_type": "asset_viewed",
            "position_seconds": 180,
            "asset_key": "slides",
            "metadata": {"source": "lesson-player"},
        },
    )
    assert event.status_code == 201
    event_payload = event.json()
    assert event_payload["activityType"] == "asset_viewed"

    second = TestClient(
        create_app(
            settings=_settings(),
            catalog=CourseCatalog(FIXTURE_DATA_ROOT),
            state_store=TrainingStateStore(
                persistence=JsonFileTrainingPersistence(state_path),
                sandbox_execution_enabled=False,
            ),
        )
    )
    progress = second.get("/api/v1/training/me/progress", headers=headers).json()
    f1_progress = progress["lessonProgress"]["F1"]
    assert f1_progress["resumeLessonId"] == "F1-L2"
    assert f1_progress["lastActivityAt"] == event_payload["createdAt"]
    assert f1_progress["activityEvents"][0]["positionSeconds"] == 180


def test_lesson_completion_records_required_activity_event():
    client = _client()
    headers = {"x-user-id": "learner-a"}
    client.post(
        "/api/v1/training/enrollments", headers=headers, json={"course_id": "F1"}
    )

    completed = client.post(
        "/api/v1/training/lessons/complete",
        headers=headers,
        json={
            "course_id": "F1",
            "lesson_id": "F1-L1",
            "content": "Completed the required activity.",
        },
    )

    assert completed.status_code == 201
    progress = client.get("/api/v1/training/me/progress", headers=headers).json()
    f1_progress = progress["lessonProgress"]["F1"]
    assert f1_progress["completedLessons"] == ["F1-L1"]
    assert f1_progress["resumeLessonId"] == "F1-L1"
    assert f1_progress["activityEvents"][-1]["activityType"] == "lesson_completed"
    assert f1_progress["activityEvents"][-1]["required"] is True


def test_offline_cohort_assignment_attendance_timeline_and_proof_flow():
    client = _client()
    admin_headers = {
        "x-user-id": "operator-a",
        "x-user-roles": "operator",
        "x-organization-id": "org-a",
    }
    learner_headers = {"x-user-id": "learner-a"}

    created = client.post(
        "/api/v1/training/admin/cohorts",
        headers=admin_headers,
        json={
            "organization_id": "org-a",
            "name": "May offline workshop",
            "path_code": "F",
            "course_ids": ["F1"],
            "learner_ids": [],
            "start_at": "2026-05-26T09:00:00Z",
            "end_at": "2026-05-26T17:00:00Z",
            "delivery_status": "scheduled",
        },
    )
    assert created.status_code == 201
    cohort = created.json()
    assert cohort["deliveryStatus"] == "scheduled"
    assert cohort["startAt"] == "2026-05-26T09:00:00Z"

    assigned = client.post(
        f"/api/v1/training/admin/cohorts/{cohort['id']}/enrollments",
        headers=admin_headers,
        json={"learner_ids": ["learner-a", "learner-a"]},
    )
    assert assigned.status_code == 200
    assert assigned.json()["learnerIds"] == ["learner-a"]

    attendance = client.post(
        f"/api/v1/training/admin/cohorts/{cohort['id']}/attendance",
        headers=admin_headers,
        json={
            "learner_id": "learner-a",
            "course_id": "F1",
            "status": "present",
            "metadata": {"room": "A"},
        },
    )
    assert attendance.status_code == 201
    assert attendance.json()["eventType"] == "attendance_present"

    progress = client.get(
        "/api/v1/training/me/progress", headers=learner_headers
    ).json()
    assert progress["enrollments"][0]["courseId"] == "F1"

    timeline = client.get("/api/v1/training/me/timeline", headers=learner_headers)
    assert timeline.status_code == 200
    event_types = [event["eventType"] for event in timeline.json()["events"]]
    assert "cohort_assigned" in event_types
    assert "attendance_present" in event_types


def test_lab_submission_review_override_and_completion_proof_eligibility():
    client = _client(settings=_settings(sandbox_execution_enabled=True))
    admin_headers = {
        "x-user-id": "operator-a",
        "x-user-roles": "operator",
        "x-organization-id": "org-a",
    }
    learner_headers = {"x-user-id": "learner-a"}

    cohort = client.post(
        "/api/v1/training/admin/cohorts",
        headers=admin_headers,
        json={
            "organization_id": "org-a",
            "name": "Lab workshop",
            "path_code": "F",
            "course_ids": ["F1"],
            "learner_ids": ["learner-a"],
        },
    ).json()
    client.post(
        f"/api/v1/training/admin/cohorts/{cohort['id']}/attendance",
        headers=admin_headers,
        json={"learner_id": "learner-a", "course_id": "F1", "status": "present"},
    )

    lab = client.get("/api/v1/training/labs/F1-agent-hello", headers=learner_headers)
    assert lab.status_code == 200
    assert lab.json()["passingScore"] == 80

    failed_lab = client.post(
        "/api/v1/training/labs/F1-agent-hello/submissions",
        headers=learner_headers,
        json={"artifact": "RESULT = 'not enough'"},
    )
    assert failed_lab.status_code == 201
    failed_payload = failed_lab.json()
    assert failed_payload["passed"] is False
    assert failed_payload["proofEligible"] is False

    queue = client.get("/api/v1/training/review/queue", headers=admin_headers)
    assert queue.status_code == 200
    assert queue.json()["items"][0]["sourceType"] == "lab_submission"

    overridden = client.post(
        f"/api/v1/training/review/items/{failed_payload['submissionId']}/override",
        headers=admin_headers,
        json={
            "status": "approved",
            "score": 100,
            "passed": True,
            "reason": "Trainer verified the lab output offline.",
        },
    )
    assert overridden.status_code == 200
    assert overridden.json()["finalStatus"] == "approved"
    assert (
        overridden.json()["overrideReason"]
        == "Trainer verified the lab output offline."
    )

    client.post(
        "/api/v1/training/enrollments",
        headers=learner_headers,
        json={"course_id": "F1"},
    )
    course_detail = client.get("/api/v1/training/courses/F1").json()
    lesson_ids = [
        lesson["id"]
        for section in course_detail["sections"]
        for lesson in section["lessons"]
    ]
    for lesson_id in lesson_ids:
        client.post(
            "/api/v1/training/lessons/complete",
            headers=learner_headers,
            json={
                "course_id": "F1",
                "lesson_id": lesson_id,
                "content": "Completed offline workshop activity.",
            },
        )
    quiz = client.post(
        "/api/v1/training/quizzes/entry/attempts",
        headers=learner_headers,
    ).json()
    question_ids = quiz["questionIds"]
    answers = {question_id: "B" for question_id in question_ids}
    client.post(
        f"/api/v1/training/attempts/{quiz['id']}/submit",
        headers=learner_headers,
        json={"answers": answers},
    )

    eligibility = client.get(
        "/api/v1/training/completion-eligibility/F1",
        headers=learner_headers,
    )
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is True
    assert eligibility.json()["labStatus"] == "passed"


def test_training_routes_registry_matches_user_microservice_contract():
    route_meta = get_routes_for_consul()

    assert SERVICE_METADATA["service_name"] == "training_service"
    assert SERVICE_METADATA["port"] == 8262
    assert route_meta["base_path"] == "/api/v1/training"
    assert int(route_meta["route_count"]) == len(get_all_routes())
    assert int(route_meta["protected_count"]) > 0
