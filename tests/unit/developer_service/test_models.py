import pytest

from microservices.developer_service.models import (
    SetupStepStatus,
    WarningInfo,
    build_empty_overview,
)

pytestmark = [pytest.mark.unit, pytest.mark.tdd]


def test_empty_overview_has_required_console_contract_sections():
    overview = build_empty_overview(
        user_id="user-1",
        organization_id="org-1",
        project_id="project-1",
        period_days=14,
    )

    payload = overview.model_dump()

    assert payload["user_id"] == "user-1"
    assert payload["organization"]["id"] == "org-1"
    assert payload["selected_project"]["id"] == "project-1"
    assert set(payload) >= {
        "organization",
        "selected_project",
        "projects",
        "setup",
        "credentials",
        "first_call",
        "usage",
        "traces",
        "eval_failures",
        "next_action",
        "warnings",
    }
    assert payload["usage"]["period"]["days"] == 14


def test_empty_overview_uses_explicit_setup_statuses():
    overview = build_empty_overview(
        user_id="user-1",
        organization_id="org-1",
        project_id=None,
    )

    steps = {step.id: step for step in overview.setup.steps}

    assert steps["organization"].status == SetupStepStatus.COMPLETE
    assert steps["project"].status == SetupStepStatus.TODO
    assert steps["credential"].status == SetupStepStatus.BLOCKED
    assert steps["first_call"].status == SetupStepStatus.BLOCKED
    assert overview.setup.completed == 1
    assert overview.setup.total == len(steps)


def test_warning_info_has_source_code_and_message():
    warning = WarningInfo(
        source="project_service",
        code="dependency_not_configured",
        message="Project dependency is not wired yet.",
    )

    assert warning.model_dump() == {
        "source": "project_service",
        "code": "dependency_not_configured",
        "message": "Project dependency is not wired yet.",
    }
