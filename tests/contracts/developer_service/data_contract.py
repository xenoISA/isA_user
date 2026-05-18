"""Developer service data contract."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class DeveloperWarningContract(BaseModel):
    source: str
    code: str
    message: str


class DeveloperOrganizationContract(BaseModel):
    id: str = Field(..., min_length=1)
    name: Optional[str] = None
    role: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class DeveloperProjectContract(BaseModel):
    id: str = Field(..., min_length=1)
    name: Optional[str] = None
    status: Optional[str] = None
    is_default: bool = False


class DeveloperSetupStepContract(BaseModel):
    id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    status: str
    href: Optional[str] = None
    blocked_reason: Optional[str] = None


class DeveloperSetupProgressContract(BaseModel):
    completed: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
    steps: List[DeveloperSetupStepContract]


class DeveloperCredentialSummaryContract(BaseModel):
    api_key_count: int = Field(0, ge=0)
    service_account_count: int = Field(0, ge=0)
    has_active_credential: bool = False
    last_used_at: Optional[datetime] = None
    can_create: bool = False


class DeveloperUsagePeriodContract(BaseModel):
    start: datetime
    end: datetime
    days: int = Field(..., ge=1, le=90)


class DeveloperUsageSummaryContract(BaseModel):
    period: DeveloperUsagePeriodContract
    requests: int = Field(0, ge=0)
    tokens: int = Field(0, ge=0)
    cost_usd: float = Field(0.0, ge=0)
    currency: str = "USD"


class DeveloperOverviewContract(BaseModel):
    user_id: str = Field(..., min_length=1)
    organization: DeveloperOrganizationContract
    selected_project: Optional[DeveloperProjectContract] = None
    projects: List[DeveloperProjectContract] = Field(default_factory=list)
    setup: DeveloperSetupProgressContract
    credentials: DeveloperCredentialSummaryContract
    usage: DeveloperUsageSummaryContract
    warnings: List[DeveloperWarningContract] = Field(default_factory=list)


class DeveloperTestDataFactory:
    @staticmethod
    def overview(
        *,
        user_id: str = "usr_test",
        organization_id: str = "org_test",
        project_id: Optional[str] = None,
        period_days: int = 7,
    ) -> DeveloperOverviewContract:
        now = datetime.now(timezone.utc)
        project = (
            DeveloperProjectContract(id=project_id, status="selected")
            if project_id
            else None
        )
        steps = [
            DeveloperSetupStepContract(
                id="organization", label="Select organization", status="complete"
            ),
            DeveloperSetupStepContract(
                id="project",
                label="Create or select project",
                status="complete" if project_id else "todo",
            ),
        ]
        return DeveloperOverviewContract(
            user_id=user_id,
            organization=DeveloperOrganizationContract(id=organization_id),
            selected_project=project,
            projects=[project] if project else [],
            setup=DeveloperSetupProgressContract(
                completed=sum(1 for step in steps if step.status == "complete"),
                total=len(steps),
                steps=steps,
            ),
            credentials=DeveloperCredentialSummaryContract(can_create=bool(project_id)),
            usage=DeveloperUsageSummaryContract(
                period=DeveloperUsagePeriodContract(
                    start=now - timedelta(days=period_days),
                    end=now,
                    days=period_days,
                )
            ),
        )
