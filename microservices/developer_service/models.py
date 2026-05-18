"""Developer Service Pydantic models."""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SetupStepStatus(str, Enum):
    COMPLETE = "complete"
    TODO = "todo"
    BLOCKED = "blocked"
    READ_ONLY = "read_only"


class WarningInfo(BaseModel):
    source: str
    code: str
    message: str


class OrganizationContext(BaseModel):
    id: str
    name: Optional[str] = None
    role: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    access_level: Optional[str] = None


class ProjectSummary(BaseModel):
    id: str
    name: Optional[str] = None
    status: Optional[str] = None
    is_default: bool = False
    updated_at: Optional[datetime] = None


class SetupStep(BaseModel):
    id: str
    label: str
    status: SetupStepStatus
    href: Optional[str] = None
    blocked_reason: Optional[str] = None


class SetupProgress(BaseModel):
    completed: int
    total: int
    steps: List[SetupStep]


class CredentialSummary(BaseModel):
    api_key_count: int = 0
    service_account_count: int = 0
    has_active_credential: bool = False
    last_used_at: Optional[datetime] = None
    can_create: bool = False
    read_only_reason: Optional[str] = None


class FirstCallSummary(BaseModel):
    status: SetupStepStatus = SetupStepStatus.BLOCKED
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    at: Optional[datetime] = None
    latency_ms: Optional[int] = None
    tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    source: Optional[str] = None


class FirstCallRequest(BaseModel):
    organization_id: str = Field(..., min_length=1)
    project_id: str = Field(..., min_length=1)
    model: str = Field(default="gpt-4.1-nano", min_length=1)
    api_key_id: Optional[str] = Field(None, min_length=1)
    api_key: Optional[str] = Field(None, min_length=1, repr=False)
    service_account_id: Optional[str] = Field(None, min_length=1)
    prompt: str = Field(
        default="Reply with a short JSON object confirming Developer first-call readiness.",
        min_length=1,
        max_length=2000,
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FirstCallUsage(BaseModel):
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    tokens: int = 0
    cost_usd: float = 0.0
    currency: str = "USD"


class FirstCallRemediation(BaseModel):
    code: str
    message: str
    href: Optional[str] = None
    field: Optional[str] = None


class FirstCallResponse(BaseModel):
    success: bool
    status: str
    organization_id: str
    project_id: str
    model: str
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    trace_href: Optional[str] = None
    latency_ms: Optional[int] = None
    tokens: int = 0
    cost_usd: float = 0.0
    timestamp: datetime
    usage: FirstCallUsage = Field(default_factory=FirstCallUsage)
    remediation: Optional[FirstCallRemediation] = None
    warnings: List[WarningInfo] = Field(default_factory=list)


class UsagePeriod(BaseModel):
    start: datetime
    end: datetime
    days: int


class UsageDailyPoint(BaseModel):
    date: str
    requests: int = 0
    tokens: int = 0
    cost_usd: float = 0.0


class UsageSummary(BaseModel):
    period: UsagePeriod
    requests: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    currency: str = "USD"
    daily: List[UsageDailyPoint] = Field(default_factory=list)


class TraceSummary(BaseModel):
    trace_id: str
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    href: Optional[str] = None


class EvalFailureSummary(BaseModel):
    run_id: str
    suite_id: Optional[str] = None
    name: Optional[str] = None
    failed_cases: int = 0
    created_at: Optional[datetime] = None
    href: Optional[str] = None


class NextAction(BaseModel):
    id: str
    label: str
    href: str
    reason: str
    severity: str = "info"


class DeveloperOverviewResponse(BaseModel):
    user_id: str
    organization: OrganizationContext
    selected_project: Optional[ProjectSummary] = None
    projects: List[ProjectSummary] = Field(default_factory=list)
    setup: SetupProgress
    credentials: CredentialSummary
    first_call: FirstCallSummary
    usage: UsageSummary
    traces: List[TraceSummary] = Field(default_factory=list)
    eval_failures: List[EvalFailureSummary] = Field(default_factory=list)
    next_action: NextAction
    warnings: List[WarningInfo] = Field(default_factory=list)


class DeveloperHealthResponse(BaseModel):
    status: str
    service: str
    version: str
    dependencies: Dict[str, str]
    timestamp: datetime


def build_empty_overview(
    *,
    user_id: str,
    organization_id: str,
    project_id: Optional[str],
    period_days: int = 7,
    warnings: Optional[List[WarningInfo]] = None,
) -> DeveloperOverviewResponse:
    """Build the minimal backend-backed Developer cockpit response."""
    now = datetime.now(tz=timezone.utc)
    selected_project = (
        ProjectSummary(id=project_id, status="selected") if project_id else None
    )

    steps = [
        SetupStep(
            id="organization",
            label="Select organization",
            status=SetupStepStatus.COMPLETE,
            href="/dashboard/settings/organization",
        ),
        SetupStep(
            id="project",
            label="Create or select project",
            status=SetupStepStatus.COMPLETE if project_id else SetupStepStatus.TODO,
            href="/dashboard/projects",
        ),
        SetupStep(
            id="credential",
            label="Create project API key",
            status=SetupStepStatus.TODO if project_id else SetupStepStatus.BLOCKED,
            href="/dashboard/developer/api-keys",
            blocked_reason=None if project_id else "Select or create a project first.",
        ),
        SetupStep(
            id="first_call",
            label="Run first API call",
            status=SetupStepStatus.BLOCKED,
            href="/dashboard/developer",
            blocked_reason="Create an active project credential first.",
        ),
    ]
    completed = sum(1 for step in steps if step.status == SetupStepStatus.COMPLETE)

    if project_id:
        next_action = NextAction(
            id="create_credential",
            label="Create API key",
            href="/dashboard/developer/api-keys",
            reason="A selected project needs an active credential before the first API call.",
            severity="warning",
        )
    else:
        next_action = NextAction(
            id="create_project",
            label="Create project",
            href="/dashboard/projects",
            reason="Developer setup needs a project before credentials and usage can be attributed.",
            severity="warning",
        )

    return DeveloperOverviewResponse(
        user_id=user_id,
        organization=OrganizationContext(id=organization_id),
        selected_project=selected_project,
        projects=[selected_project] if selected_project else [],
        setup=SetupProgress(completed=completed, total=len(steps), steps=steps),
        credentials=CredentialSummary(can_create=bool(project_id)),
        first_call=FirstCallSummary(),
        usage=UsageSummary(
            period=UsagePeriod(
                start=now - timedelta(days=period_days),
                end=now,
                days=period_days,
            )
        ),
        next_action=next_action,
        warnings=warnings or [],
    )


def dependency_warning(source: str, status: str) -> WarningInfo:
    return WarningInfo(
        source=source,
        code=f"dependency_{status}",
        message=f"{source} is {status}; Developer overview is returning partial data.",
    )
