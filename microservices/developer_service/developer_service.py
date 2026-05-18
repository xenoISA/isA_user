"""Developer Journey overview aggregation service."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .models import (
    CredentialSummary,
    DeveloperHealthResponse,
    DeveloperOverviewResponse,
    FirstCallRemediation,
    FirstCallRequest,
    FirstCallResponse,
    FirstCallSummary,
    FirstCallUsage,
    NextAction,
    OrganizationContext,
    ProjectSummary,
    SetupProgress,
    SetupStep,
    SetupStepStatus,
    TraceSummary,
    UsageDailyPoint,
    UsagePeriod,
    UsageSummary,
    WarningInfo,
    build_empty_overview,
    dependency_warning,
)

CREATE_API_KEY_PERMISSIONS = {
    "auth.api_keys.create",
    "api_keys:create",
    "api_key:create",
    "keys:create",
}
WRITE_ROLES = {"owner", "admin"}
READ_ONLY_ROLES = {"viewer", "read_only", "readonly", "guest"}


class DeveloperOverviewService:
    """Thin aggregation boundary for Developer cockpit read models."""

    def __init__(
        self,
        *,
        organization_client: Optional[Any] = None,
        project_client: Optional[Any] = None,
        credential_client: Optional[Any] = None,
        billing_client: Optional[Any] = None,
        model_client: Optional[Any] = None,
        trace_client: Optional[Any] = None,
        evaluation_client: Optional[Any] = None,
    ):
        self.organization_client = organization_client
        self.project_client = project_client
        self.credential_client = credential_client
        self.billing_client = billing_client
        self.model_client = model_client
        self.trace_client = trace_client
        self.evaluation_client = evaluation_client

    async def get_overview(
        self,
        *,
        user_id: str,
        organization_id: str,
        project_id: Optional[str] = None,
        period_days: int = 7,
        auth_token: Optional[str] = None,
    ) -> DeveloperOverviewResponse:
        if not any(
            [
                self.organization_client,
                self.project_client,
                self.credential_client,
                self.billing_client,
            ]
        ):
            dependency_health = await self.get_dependency_health()
            warnings = [
                dependency_warning(source, status)
                for source, status in dependency_health.items()
                if status != "healthy"
            ]
            return build_empty_overview(
                user_id=user_id,
                organization_id=organization_id,
                project_id=project_id,
                period_days=period_days,
                warnings=warnings,
            )

        (
            organization_result,
            projects_result,
            credentials_result,
            usage_result,
        ) = await asyncio.gather(
            self._load_source(
                "organization_service",
                self.organization_client,
                lambda: self._fetch_organization_context(
                    user_id=user_id,
                    organization_id=organization_id,
                ),
            ),
            self._load_source(
                "project_service",
                self.project_client,
                lambda: self._fetch_projects(
                    user_id=user_id,
                    organization_id=organization_id,
                    auth_token=auth_token,
                ),
            ),
            self._load_source(
                "auth_service",
                self.credential_client,
                lambda: self._fetch_credentials(
                    organization_id=organization_id,
                    auth_token=auth_token,
                ),
            ),
            self._load_source(
                "billing_service",
                self.billing_client,
                lambda: self._fetch_usage(
                    user_id=user_id,
                    organization_id=organization_id,
                    project_id=project_id,
                    period_days=period_days,
                ),
            ),
        )

        warnings = [
            warning
            for _, warning in (
                organization_result,
                projects_result,
                credentials_result,
                usage_result,
            )
            if warning is not None
        ]

        organization_payload = organization_result[0] or {
            "context": OrganizationContext(id=organization_id),
            "found": None,
        }
        projects = projects_result[0] or []
        credential_keys = credentials_result[0] or []
        usage_payload = usage_result[0]

        warning_from_usage = self._warning_from_usage_payload(usage_payload)
        if warning_from_usage:
            warnings.extend(warning_from_usage)

        return self._build_overview(
            user_id=user_id,
            organization_id=organization_id,
            project_id=project_id,
            period_days=period_days,
            organization_context=organization_payload["context"],
            organization_found=organization_payload["found"],
            projects=projects,
            credential_keys=credential_keys,
            usage_payload=usage_payload,
            warnings=warnings,
        )

    async def run_first_call(
        self,
        *,
        user_id: str,
        request: FirstCallRequest,
        auth_token: Optional[str] = None,
    ) -> FirstCallResponse:
        warnings: List[WarningInfo] = []

        project_valid, project_warning = await self._validate_first_call_project(
            user_id=user_id,
            organization_id=request.organization_id,
            project_id=request.project_id,
            auth_token=auth_token,
        )
        if project_warning:
            warnings.append(project_warning)
        if project_valid is False:
            return self._first_call_failure(
                request=request,
                status="missing_project",
                remediation=FirstCallRemediation(
                    code="project_not_found",
                    message="Select or create a project before running the first API call.",
                    href="/dashboard/projects",
                    field="project_id",
                ),
                warnings=warnings,
            )

        (
            credential_valid,
            credential_result,
            credential_warning,
        ) = await self._validate_first_call_credential(
            request=request,
            auth_token=auth_token,
        )
        if credential_warning:
            warnings.append(credential_warning)
        if not credential_valid:
            return self._first_call_failure(
                request=request,
                status="invalid_key",
                remediation=FirstCallRemediation(
                    code="credential_unavailable",
                    message="Create or select an active project API key before running the first call.",
                    href="/dashboard/developer/api-keys",
                    field="api_key_id",
                ),
                warnings=warnings,
            )

        if not self.model_client:
            return self._first_call_failure(
                request=request,
                status="model_unavailable",
                remediation=FirstCallRemediation(
                    code="model_service_not_configured",
                    message="Model execution is not configured for Developer first-call verification.",
                    href="/dashboard/developer",
                ),
                warnings=warnings,
            )

        try:
            started = datetime.now(tz=timezone.utc)
            model_result = await self._execute_model_first_call(
                user_id=user_id,
                request=request,
                credential_result=credential_result,
                auth_token=auth_token,
            )
            response = self._normalize_first_call_success(
                request=request,
                payload=model_result,
                started_at=started,
                warnings=warnings,
            )
        except Exception:
            return self._first_call_failure(
                request=request,
                status="model_failed",
                remediation=FirstCallRemediation(
                    code="model_call_failed",
                    message="The model call failed. Check the selected model and credential scope.",
                    href="/dashboard/developer",
                    field="model",
                ),
                warnings=warnings,
            )

        trace_warning = await self._enrich_first_call_trace(response)
        if trace_warning:
            response.warnings.append(trace_warning)
        return response

    async def get_dependency_health(self) -> Dict[str, str]:
        clients = {
            "organization_service": self.organization_client,
            "project_service": self.project_client,
            "auth_service": self.credential_client,
            "billing_service": self.billing_client,
            "model_service": self.model_client,
            "trace_service": self.trace_client,
            "evaluation_service": self.evaluation_client,
        }
        statuses = await asyncio.gather(
            *(self._client_health(client) for client in clients.values())
        )
        return dict(zip(clients.keys(), statuses))

    async def health_response(self, *, version: str) -> DeveloperHealthResponse:
        dependencies = await self.get_dependency_health()
        status = (
            "healthy"
            if all(value == "healthy" for value in dependencies.values())
            else "degraded"
        )
        from datetime import datetime, timezone

        return DeveloperHealthResponse(
            status=status,
            service="developer_service",
            version=version,
            dependencies=dependencies,
            timestamp=datetime.now(tz=timezone.utc),
        )

    async def _client_health(self, client: Optional[Any]) -> str:
        if client is None:
            return "not_configured"

        health = getattr(client, "health", None)
        if health is None:
            return "healthy"

        try:
            result = health()
            if hasattr(result, "__await__"):
                result = await result
            return "healthy" if result else "unhealthy"
        except Exception:
            return "unhealthy"

    async def close(self) -> None:
        for client in (
            self.organization_client,
            self.project_client,
            self.credential_client,
            self.billing_client,
            self.model_client,
            self.trace_client,
            self.evaluation_client,
        ):
            if client is None:
                continue
            close = getattr(client, "close", None)
            if close is None:
                continue
            result = close()
            if hasattr(result, "__await__"):
                await result

    async def _load_source(
        self,
        source: str,
        client: Optional[Any],
        awaitable_factory,
    ) -> Tuple[Optional[Any], Optional[WarningInfo]]:
        if client is None:
            return None, dependency_warning(source, "not_configured")

        try:
            return await awaitable_factory(), None
        except Exception as exc:
            code = (
                "dependency_timeout"
                if self._is_timeout(exc)
                else "dependency_unavailable"
            )
            return (
                None,
                WarningInfo(
                    source=source,
                    code=code,
                    message=f"{source} is unavailable; Developer overview is returning partial data.",
                ),
            )

    async def _fetch_organization_context(
        self, *, user_id: str, organization_id: str
    ) -> Dict[str, Any]:
        client = self.organization_client
        context_method = getattr(client, "get_organization_context", None)
        if context_method:
            payload = await self._invoke(
                context_method,
                [
                    ((), {"user_id": user_id, "organization_id": organization_id}),
                    ((user_id, organization_id), {}),
                    ((organization_id, user_id), {}),
                ],
            )
            return self._normalize_organization_payload(
                payload, organization_id=organization_id, user_id=user_id
            )

        organization = None
        member = None
        get_organization = getattr(client, "get_organization", None)
        if get_organization:
            organization = await self._invoke(
                get_organization,
                [
                    ((organization_id, user_id), {}),
                    ((), {"organization_id": organization_id, "user_id": user_id}),
                    ((organization_id,), {}),
                ],
            )

        member_method = getattr(client, "get_member_role", None) or getattr(
            client, "_get_member_role", None
        )
        if member_method:
            member = await self._invoke(
                member_method,
                [
                    ((organization_id, user_id), {}),
                    ((), {"organization_id": organization_id, "user_id": user_id}),
                ],
            )
        else:
            members_method = getattr(client, "get_members", None)
            if members_method:
                members = await self._invoke(
                    members_method,
                    [
                        ((organization_id, user_id), {}),
                        ((), {"organization_id": organization_id, "user_id": user_id}),
                    ],
                )
                member = self._find_member_for_user(members, user_id)

        return self._normalize_organization_payload(
            {"organization": organization, "member": member},
            organization_id=organization_id,
            user_id=user_id,
        )

    async def _fetch_projects(
        self,
        *,
        user_id: str,
        organization_id: str,
        auth_token: Optional[str],
    ) -> List[ProjectSummary]:
        list_projects = getattr(self.project_client, "list_projects")
        payload = await self._invoke(
            list_projects,
            [
                (
                    (),
                    {
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "auth_token": auth_token,
                        "limit": 50,
                        "offset": 0,
                    },
                ),
                (
                    (auth_token or "",),
                    {"organization_id": organization_id, "limit": 50, "offset": 0},
                ),
                ((auth_token or "", 50, 0, organization_id), {}),
                ((user_id, organization_id), {}),
            ],
        )
        return [
            self._normalize_project(project)
            for project in self._extract_list(payload, "projects")
        ]

    async def _fetch_credentials(
        self,
        *,
        organization_id: str,
        auth_token: Optional[str],
    ) -> List[Dict[str, Any]]:
        list_api_keys = getattr(self.credential_client, "list_api_keys")
        payload = await self._invoke(
            list_api_keys,
            [
                (
                    (),
                    {
                        "organization_id": organization_id,
                        "auth_token": auth_token,
                        "project_id": None,
                    },
                ),
                ((organization_id,), {"auth_token": auth_token, "project_id": None}),
                ((organization_id, auth_token), {}),
                ((organization_id,), {}),
            ],
        )
        return [self._as_dict(item) for item in self._extract_list(payload, "api_keys")]

    async def _fetch_usage(
        self,
        *,
        user_id: str,
        organization_id: str,
        project_id: Optional[str],
        period_days: int,
    ) -> Optional[Dict[str, Any]]:
        method = (
            getattr(self.billing_client, "get_developer_usage", None)
            or getattr(self.billing_client, "get_usage_overview", None)
            or getattr(self.billing_client, "get_usage_aggregations", None)
        )
        payload = await self._invoke(
            method,
            [
                (
                    (),
                    {
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "project_id": project_id,
                        "period_days": period_days,
                    },
                ),
                (
                    (),
                    {
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "period_days": period_days,
                    },
                ),
                ((user_id, period_days, organization_id), {}),
                ((user_id, organization_id, period_days), {}),
            ],
        )
        return self._as_dict(payload) if payload is not None else None

    async def _validate_first_call_project(
        self,
        *,
        user_id: str,
        organization_id: str,
        project_id: str,
        auth_token: Optional[str],
    ) -> Tuple[Optional[bool], Optional[WarningInfo]]:
        if not self.project_client:
            return None, dependency_warning("project_service", "not_configured")
        result, warning = await self._load_source(
            "project_service",
            self.project_client,
            lambda: self._fetch_projects(
                user_id=user_id,
                organization_id=organization_id,
                auth_token=auth_token,
            ),
        )
        if warning:
            return None, warning
        projects = result or []
        return any(project.id == project_id for project in projects), None

    async def _validate_first_call_credential(
        self,
        *,
        request: FirstCallRequest,
        auth_token: Optional[str],
    ) -> Tuple[bool, Dict[str, Any], Optional[WarningInfo]]:
        if not self.credential_client:
            return (
                False,
                {},
                dependency_warning("auth_service", "not_configured"),
            )

        if request.api_key:
            verify_method = getattr(self.credential_client, "verify_api_key", None)
            if verify_method is None:
                return (
                    False,
                    {},
                    WarningInfo(
                        source="auth_service",
                        code="dependency_unavailable",
                        message="auth_service cannot verify plaintext API keys for first-call.",
                    ),
                )
            try:
                result = await self._invoke(
                    verify_method,
                    [
                        (
                            (),
                            {
                                "api_key": request.api_key,
                                "project_id": request.project_id,
                            },
                        ),
                        ((request.api_key,), {"project_id": request.project_id}),
                        ((request.api_key, request.project_id), {}),
                    ],
                )
            except Exception as exc:
                return (
                    False,
                    {},
                    WarningInfo(
                        source="auth_service",
                        code="dependency_timeout"
                        if self._is_timeout(exc)
                        else "dependency_unavailable",
                        message="auth_service could not verify the API key.",
                    ),
                )
            result_data = self._as_dict(result)
            if not result_data.get("valid"):
                return False, result_data, None
            return True, result_data, None

        result, warning = await self._load_source(
            "auth_service",
            self.credential_client,
            lambda: self._fetch_credentials(
                organization_id=request.organization_id,
                auth_token=auth_token,
            ),
        )
        if warning:
            return False, {}, warning
        for key in result or []:
            if request.api_key_id and key.get("key_id") != request.api_key_id:
                continue
            if (
                request.service_account_id
                and key.get("service_account_id") != request.service_account_id
            ):
                continue
            if self._is_active_key(key) and self._key_matches_project(
                key, request.project_id
            ):
                return True, key, None
        return False, {}, None

    async def _execute_model_first_call(
        self,
        *,
        user_id: str,
        request: FirstCallRequest,
        credential_result: Dict[str, Any],
        auth_token: Optional[str],
    ) -> Dict[str, Any]:
        method = (
            getattr(self.model_client, "run_first_call", None)
            or getattr(self.model_client, "create_chat_completion", None)
            or getattr(self.model_client, "chat_completion", None)
            or getattr(self.model_client, "complete", None)
        )
        result = await self._invoke(
            method,
            [
                (
                    (),
                    {
                        "user_id": user_id,
                        "organization_id": request.organization_id,
                        "project_id": request.project_id,
                        "model": request.model,
                        "prompt": request.prompt,
                        "api_key": request.api_key,
                        "api_key_id": request.api_key_id
                        or credential_result.get("key_id"),
                        "auth_token": auth_token,
                        "metadata": request.metadata,
                    },
                ),
                (
                    (),
                    {
                        "organization_id": request.organization_id,
                        "project_id": request.project_id,
                        "model": request.model,
                        "prompt": request.prompt,
                    },
                ),
            ],
        )
        return self._as_dict(result)

    async def _enrich_first_call_trace(
        self, response: FirstCallResponse
    ) -> Optional[WarningInfo]:
        if not response.trace_id or not self.trace_client:
            return None
        method = (
            getattr(self.trace_client, "get_trace", None)
            or getattr(self.trace_client, "lookup_trace", None)
            or getattr(self.trace_client, "get_trace_summary", None)
        )
        if method is None:
            return None
        try:
            payload = await self._invoke(
                method,
                [
                    ((response.trace_id,), {}),
                    ((), {"trace_id": response.trace_id}),
                ],
            )
            trace = self._as_dict(payload)
            response.trace_href = (
                trace.get("href") or trace.get("url") or response.trace_href
            )
            if trace.get("duration_ms") and response.latency_ms is None:
                response.latency_ms = int(trace["duration_ms"])
            return None
        except Exception:
            return WarningInfo(
                source="trace_service",
                code="trace_lookup_unavailable",
                message="Trace lookup failed; first-call result returned model evidence only.",
            )

    def _build_overview(
        self,
        *,
        user_id: str,
        organization_id: str,
        project_id: Optional[str],
        period_days: int,
        organization_context: OrganizationContext,
        organization_found: Optional[bool],
        projects: List[ProjectSummary],
        credential_keys: List[Dict[str, Any]],
        usage_payload: Optional[Dict[str, Any]],
        warnings: List[WarningInfo],
    ) -> DeveloperOverviewResponse:
        selected_project = self._select_project(projects, project_id)
        credentials = self._summarize_credentials(
            credential_keys=credential_keys,
            selected_project_id=selected_project.id if selected_project else None,
            organization=organization_context,
            organization_found=organization_found,
        )
        usage = self._normalize_usage(usage_payload, period_days=period_days)

        has_usage = usage.requests > 0 or usage.tokens > 0 or usage.cost_usd > 0
        steps = self._build_setup_steps(
            organization_found=organization_found,
            selected_project=selected_project,
            has_active_credential=credentials.has_active_credential,
            can_create_credentials=credentials.can_create,
            has_usage=has_usage,
        )
        setup = SetupProgress(
            completed=sum(
                1 for step in steps if step.status == SetupStepStatus.COMPLETE
            ),
            total=len(steps),
            steps=steps,
        )
        first_call_status = steps[-1].status
        first_call = FirstCallSummary(
            status=first_call_status,
            tokens=usage.tokens if has_usage else None,
            cost_usd=usage.cost_usd if has_usage else None,
            source="billing_service" if has_usage else None,
        )

        return DeveloperOverviewResponse(
            user_id=user_id,
            organization=organization_context,
            selected_project=selected_project,
            projects=projects,
            setup=setup,
            credentials=credentials,
            first_call=first_call,
            usage=usage,
            traces=self._normalize_traces(usage_payload),
            eval_failures=[],
            next_action=self._next_action(steps),
            warnings=warnings,
        )

    def _normalize_organization_payload(
        self,
        payload: Any,
        *,
        organization_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        if payload is None:
            return {
                "context": OrganizationContext(id=organization_id, status="missing"),
                "found": False,
            }

        payload = self._as_dict(payload)
        if not payload:
            return {
                "context": OrganizationContext(id=organization_id, status="missing"),
                "found": False,
            }
        organization = self._as_dict(payload.get("organization") or payload)
        member = self._as_dict(payload.get("member") or payload.get("membership"))
        if not member:
            member = self._find_member_for_user(payload.get("members"), user_id)

        organization_id_value = (
            organization.get("id")
            or organization.get("organization_id")
            or payload.get("organization_id")
            or organization_id
        )
        role = member.get("role") or organization.get("role") or payload.get("role")
        permissions = self._normalize_permissions(
            member.get("permissions")
            or organization.get("permissions")
            or payload.get("permissions")
        )

        context = OrganizationContext(
            id=str(organization_id_value),
            name=organization.get("name") or organization.get("org_name"),
            role=role,
            permissions=permissions,
            status=member.get("status") or organization.get("status"),
            access_level=member.get("access_level")
            or organization.get("access_level")
            or role,
        )
        return {"context": context, "found": True}

    def _normalize_project(self, payload: Any) -> ProjectSummary:
        data = self._as_dict(payload)
        return ProjectSummary(
            id=str(data.get("id") or data.get("project_id")),
            name=data.get("name") or data.get("project_name"),
            status=data.get("status"),
            is_default=bool(data.get("is_default") or data.get("default")),
            updated_at=self._parse_datetime(data.get("updated_at")),
        )

    def _normalize_usage(
        self, payload: Optional[Dict[str, Any]], *, period_days: int
    ) -> UsageSummary:
        now = datetime.now(tz=timezone.utc)
        if not payload:
            return UsageSummary(
                period=UsagePeriod(
                    start=now - timedelta(days=period_days),
                    end=now,
                    days=period_days,
                )
            )

        period_payload = self._as_dict(payload.get("period"))
        period_start = self._parse_datetime(period_payload.get("start")) or (
            now - timedelta(days=period_days)
        )
        period_end = self._parse_datetime(period_payload.get("end")) or now
        days = int(period_payload.get("days") or period_days)

        totals = self._as_dict(payload.get("totals") or payload)
        daily = [
            UsageDailyPoint(
                date=str(point.get("date") or point.get("period") or ""),
                requests=int(point.get("requests") or point.get("count") or 0),
                tokens=int(point.get("tokens") or point.get("total_usage_amount") or 0),
                cost_usd=float(
                    point.get("cost_usd")
                    if point.get("cost_usd") is not None
                    else point.get("cost", 0.0)
                ),
            )
            for point in (self._extract_list(payload, "daily") or [])
        ]

        return UsageSummary(
            period=UsagePeriod(start=period_start, end=period_end, days=days),
            requests=int(totals.get("requests") or totals.get("total_count") or 0),
            tokens=int(totals.get("tokens") or totals.get("total_usage_amount") or 0),
            cost_usd=float(
                totals.get("cost_usd")
                if totals.get("cost_usd") is not None
                else totals.get("cost", 0.0)
            ),
            currency=str(totals.get("currency") or "USD"),
            daily=daily,
        )

    def _summarize_credentials(
        self,
        *,
        credential_keys: List[Dict[str, Any]],
        selected_project_id: Optional[str],
        organization: OrganizationContext,
        organization_found: Optional[bool],
    ) -> CredentialSummary:
        active_keys = [key for key in credential_keys if self._is_active_key(key)]
        project_active_keys = [
            key
            for key in active_keys
            if self._key_matches_project(key, selected_project_id)
        ]
        can_create = self._can_create_credentials(
            organization, assume_allowed=organization_found is None
        )
        service_account_ids = {
            str(key.get("service_account_id"))
            for key in credential_keys
            if key.get("service_account_id")
        }
        service_account_count = len(service_account_ids) + sum(
            1 for key in credential_keys if key.get("owner_type") == "service_account"
        )
        last_used_values = [
            parsed
            for parsed in (
                self._parse_datetime(key.get("last_used_at") or key.get("last_used"))
                for key in active_keys
            )
            if parsed is not None
        ]
        read_only_reason = None
        if not can_create:
            read_only_reason = (
                "Caller lacks permission to create Developer credentials."
            )

        return CredentialSummary(
            api_key_count=len(credential_keys),
            service_account_count=service_account_count,
            has_active_credential=bool(project_active_keys),
            last_used_at=max(last_used_values) if last_used_values else None,
            can_create=can_create,
            read_only_reason=read_only_reason,
        )

    def _build_setup_steps(
        self,
        *,
        organization_found: Optional[bool],
        selected_project: Optional[ProjectSummary],
        has_active_credential: bool,
        can_create_credentials: bool,
        has_usage: bool,
    ) -> List[SetupStep]:
        organization_status = (
            SetupStepStatus.TODO
            if organization_found is False
            else SetupStepStatus.COMPLETE
        )
        project_status = (
            SetupStepStatus.BLOCKED
            if organization_status != SetupStepStatus.COMPLETE
            else SetupStepStatus.COMPLETE
            if selected_project
            else SetupStepStatus.TODO
        )
        credential_status = self._credential_step_status(
            project_status=project_status,
            has_active_credential=has_active_credential,
            can_create_credentials=can_create_credentials,
        )
        first_call_status = self._first_call_step_status(
            selected_project=selected_project,
            credential_status=credential_status,
            has_usage=has_usage,
        )

        return [
            SetupStep(
                id="organization",
                label="Select organization",
                status=organization_status,
                href="/dashboard/settings/organization",
                blocked_reason=(
                    "Choose an organization before creating Developer resources."
                    if organization_status == SetupStepStatus.TODO
                    else None
                ),
            ),
            SetupStep(
                id="project",
                label="Create or select project",
                status=project_status,
                href="/dashboard/projects",
                blocked_reason=(
                    "Select an organization before creating a project."
                    if project_status == SetupStepStatus.BLOCKED
                    else None
                ),
            ),
            SetupStep(
                id="credential",
                label="Create project API key",
                status=credential_status,
                href="/dashboard/developer/api-keys",
                blocked_reason=self._credential_blocked_reason(
                    project_status, credential_status
                ),
            ),
            SetupStep(
                id="first_call",
                label="Run first API call",
                status=first_call_status,
                href="/dashboard/developer",
                blocked_reason=self._first_call_blocked_reason(
                    selected_project, credential_status, first_call_status
                ),
            ),
        ]

    def _credential_step_status(
        self,
        *,
        project_status: SetupStepStatus,
        has_active_credential: bool,
        can_create_credentials: bool,
    ) -> SetupStepStatus:
        if project_status != SetupStepStatus.COMPLETE:
            return SetupStepStatus.BLOCKED
        if has_active_credential:
            return SetupStepStatus.COMPLETE
        if not can_create_credentials:
            return SetupStepStatus.READ_ONLY
        return SetupStepStatus.TODO

    def _first_call_step_status(
        self,
        *,
        selected_project: Optional[ProjectSummary],
        credential_status: SetupStepStatus,
        has_usage: bool,
    ) -> SetupStepStatus:
        if has_usage:
            return SetupStepStatus.COMPLETE
        if not selected_project:
            return SetupStepStatus.BLOCKED
        if credential_status == SetupStepStatus.COMPLETE:
            return SetupStepStatus.TODO
        if credential_status == SetupStepStatus.READ_ONLY:
            return SetupStepStatus.READ_ONLY
        return SetupStepStatus.BLOCKED

    def _credential_blocked_reason(
        self, project_status: SetupStepStatus, credential_status: SetupStepStatus
    ) -> Optional[str]:
        if credential_status == SetupStepStatus.BLOCKED:
            return (
                "Select or create a project first."
                if project_status != SetupStepStatus.BLOCKED
                else "Select an organization and project first."
            )
        if credential_status == SetupStepStatus.READ_ONLY:
            return "Caller lacks permission to create API keys."
        return None

    def _first_call_blocked_reason(
        self,
        selected_project: Optional[ProjectSummary],
        credential_status: SetupStepStatus,
        first_call_status: SetupStepStatus,
    ) -> Optional[str]:
        if first_call_status in {SetupStepStatus.COMPLETE, SetupStepStatus.TODO}:
            return None
        if not selected_project:
            return "Select or create a project first."
        if credential_status == SetupStepStatus.READ_ONLY:
            return "Ask an organization admin to create a project credential."
        return "Create an active project credential first."

    def _next_action(self, steps: List[SetupStep]) -> NextAction:
        for step in steps:
            if step.status == SetupStepStatus.COMPLETE:
                continue
            if step.id == "organization":
                return NextAction(
                    id="select_organization",
                    label="Select organization",
                    href="/dashboard/settings/organization",
                    reason="Developer setup needs an organization context.",
                    severity="warning",
                )
            if step.id == "project":
                return NextAction(
                    id="create_project",
                    label="Create project",
                    href="/dashboard/projects",
                    reason="Developer setup needs a project before credentials and usage can be attributed.",
                    severity="warning",
                )
            if step.id == "credential" and step.status == SetupStepStatus.READ_ONLY:
                return NextAction(
                    id="request_api_key_access",
                    label="Request API key access",
                    href="/dashboard/settings/organization",
                    reason="This user can inspect Developer setup but cannot create credentials.",
                    severity="info",
                )
            if step.id == "credential":
                return NextAction(
                    id="create_credential",
                    label="Create API key",
                    href="/dashboard/developer/api-keys",
                    reason="A selected project needs an active credential before the first API call.",
                    severity="warning",
                )
            if step.id == "first_call":
                return NextAction(
                    id="run_first_call",
                    label="Run first API call",
                    href="/dashboard/developer",
                    reason="An active credential is ready; run a first call to verify traces and usage.",
                    severity="info",
                )
        return NextAction(
            id="view_usage",
            label="View usage",
            href="/dashboard/developer/usage",
            reason="Developer setup is complete.",
            severity="info",
        )

    def _normalize_first_call_success(
        self,
        *,
        request: FirstCallRequest,
        payload: Dict[str, Any],
        started_at: datetime,
        warnings: List[WarningInfo],
    ) -> FirstCallResponse:
        usage_payload = self._as_dict(
            payload.get("usage") or payload.get("token_usage")
        )
        input_tokens = usage_payload.get("input_tokens") or usage_payload.get(
            "prompt_tokens"
        )
        output_tokens = usage_payload.get("output_tokens") or usage_payload.get(
            "completion_tokens"
        )
        tokens = (
            payload.get("tokens")
            or usage_payload.get("tokens")
            or usage_payload.get("total_tokens")
            or (int(input_tokens or 0) + int(output_tokens or 0))
        )
        cost_usd = (
            payload.get("cost_usd")
            if payload.get("cost_usd") is not None
            else usage_payload.get("cost_usd")
            if usage_payload.get("cost_usd") is not None
            else usage_payload.get("cost", 0.0)
        )
        timestamp = (
            self._parse_datetime(payload.get("timestamp") or payload.get("created_at"))
            or started_at
        )
        latency_ms = payload.get("latency_ms") or payload.get("duration_ms")
        if latency_ms is not None:
            latency_ms = int(latency_ms)
        trace_href = (
            payload.get("trace_href")
            or payload.get("trace_url")
            or payload.get("trace_link")
        )

        return FirstCallResponse(
            success=True,
            status="succeeded",
            organization_id=request.organization_id,
            project_id=request.project_id,
            model=request.model,
            request_id=payload.get("request_id") or payload.get("id"),
            trace_id=payload.get("trace_id")
            or self._as_dict(payload.get("metadata")).get("trace_id"),
            trace_href=trace_href,
            latency_ms=latency_ms,
            tokens=int(tokens or 0),
            cost_usd=float(cost_usd or 0.0),
            timestamp=timestamp,
            usage=FirstCallUsage(
                input_tokens=int(input_tokens) if input_tokens is not None else None,
                output_tokens=int(output_tokens) if output_tokens is not None else None,
                tokens=int(tokens or 0),
                cost_usd=float(cost_usd or 0.0),
                currency=str(usage_payload.get("currency") or "USD"),
            ),
            warnings=list(warnings),
        )

    def _first_call_failure(
        self,
        *,
        request: FirstCallRequest,
        status: str,
        remediation: FirstCallRemediation,
        warnings: List[WarningInfo],
    ) -> FirstCallResponse:
        return FirstCallResponse(
            success=False,
            status=status,
            organization_id=request.organization_id,
            project_id=request.project_id,
            model=request.model,
            timestamp=datetime.now(tz=timezone.utc),
            remediation=remediation,
            warnings=list(warnings),
        )

    def _select_project(
        self, projects: List[ProjectSummary], project_id: Optional[str]
    ) -> Optional[ProjectSummary]:
        if project_id:
            for project in projects:
                if project.id == project_id:
                    return project
            return ProjectSummary(id=project_id, status="selected")
        for project in projects:
            if project.is_default:
                return project
        return projects[0] if projects else None

    def _normalize_traces(
        self, usage_payload: Optional[Dict[str, Any]]
    ) -> List[TraceSummary]:
        if not usage_payload:
            return []
        return [
            TraceSummary(
                trace_id=str(trace.get("trace_id")),
                status=trace.get("status"),
                started_at=self._parse_datetime(trace.get("started_at")),
                duration_ms=trace.get("duration_ms"),
                tokens=trace.get("tokens"),
                cost_usd=trace.get("cost_usd"),
                href=trace.get("href"),
            )
            for trace in self._extract_list(usage_payload, "traces")
            if trace.get("trace_id")
        ]

    def _warning_from_usage_payload(
        self, usage_payload: Optional[Dict[str, Any]]
    ) -> List[WarningInfo]:
        if not usage_payload:
            return []
        warnings: List[WarningInfo] = []
        for raw_warning in usage_payload.get("warnings") or []:
            code = str(raw_warning)
            warnings.append(
                WarningInfo(
                    source="billing_service",
                    code=code,
                    message=f"Billing usage source reported {code}.",
                )
            )
        return warnings

    async def _invoke(self, method: Any, attempts: Iterable[Tuple[Tuple, Dict]]) -> Any:
        last_error: Optional[Exception] = None
        for args, kwargs in attempts:
            try:
                result = method(
                    *args, **{k: v for k, v in kwargs.items() if v is not None}
                )
                if hasattr(result, "__await__"):
                    result = await result
                return result
            except TypeError as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise TypeError("No invocation attempts were provided")

    def _find_member_for_user(self, members: Any, user_id: str) -> Dict[str, Any]:
        for member in self._extract_list(members, "members"):
            data = self._as_dict(member)
            member_user_id = data.get("user_id") or data.get("member_user_id")
            if member_user_id == user_id:
                return data
        return {}

    def _extract_list(self, payload: Any, key: str) -> List[Dict[str, Any]]:
        payload = self._as_dict(payload)
        if not payload:
            return []
        if isinstance(payload, list):
            return [self._as_dict(item) for item in payload]
        value = payload.get(key)
        if value is None:
            value = (
                payload.get("items") or payload.get("results") or payload.get("data")
            )
        if value is None:
            return []
        if isinstance(value, list):
            return [self._as_dict(item) for item in value]
        return []

    def _as_dict(self, payload: Any) -> Dict[str, Any]:
        if payload is None:
            return {}
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list):
            return payload  # type: ignore[return-value]
        model_dump = getattr(payload, "model_dump", None)
        if model_dump:
            return model_dump()
        dict_method = getattr(payload, "dict", None)
        if dict_method:
            return dict_method()
        return {}

    def _normalize_permissions(self, permissions: Any) -> List[str]:
        if permissions is None:
            return []
        if isinstance(permissions, str):
            return [item for item in permissions.split() if item]
        if isinstance(permissions, list):
            return [str(item) for item in permissions]
        return []

    def _can_create_credentials(
        self, organization: OrganizationContext, *, assume_allowed: bool = False
    ) -> bool:
        role = (organization.role or "").lower()
        if role in WRITE_ROLES:
            return True
        if role in READ_ONLY_ROLES:
            return False
        permissions = {permission.lower() for permission in organization.permissions}
        if permissions & CREATE_API_KEY_PERMISSIONS:
            return True
        return assume_allowed

    def _is_active_key(self, key: Dict[str, Any]) -> bool:
        if key.get("is_active") is False:
            return False
        expires_at = self._parse_datetime(key.get("expires_at"))
        if expires_at and expires_at < datetime.now(tz=timezone.utc):
            return False
        return True

    def _key_matches_project(
        self, key: Dict[str, Any], selected_project_id: Optional[str]
    ) -> bool:
        if selected_project_id is None:
            return True
        key_project_id = key.get("project_id")
        owner_type = key.get("owner_type") or "organization"
        return key_project_id == selected_project_id or (
            owner_type == "organization" and not key_project_id
        )

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def _is_timeout(self, exc: Exception) -> bool:
        return (
            isinstance(exc, asyncio.TimeoutError)
            or "timeout" in exc.__class__.__name__.lower()
        )
