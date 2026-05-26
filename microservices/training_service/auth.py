"""Request identity helpers for authenticated training actions."""

from __future__ import annotations

import json
from typing import Any
from urllib import error, request as urlrequest

from fastapi import HTTPException, Request, status

AUTH_REQUIRED_DETAIL = "Training actions require a signed-in local session."
TRUSTED_GATEWAY_HEADER = "x-isa-gateway-verified"
_IDENTITY_CACHE_KEY = "_isa_training_identity"


def _auth_mode(request: Request) -> str:
    settings = getattr(request.app.state, "settings", None)
    return str(getattr(settings, "auth_mode", "development")).lower()


def _truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() in {"1", "true", "yes", "on"})


def _requires_gateway_verification(request: Request) -> bool:
    return _auth_mode(request) in {"gateway", "production", "prod"}


def _gateway_verified(request: Request) -> bool:
    return _truthy(request.headers.get(TRUSTED_GATEWAY_HEADER))


def _auth_service_url(request: Request) -> str:
    settings = getattr(request.app.state, "settings", None)
    return str(getattr(settings, "auth_service_url", "http://localhost:8201")).rstrip(
        "/"
    )


def _bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _verify_bearer_token(token: str, request: Request) -> dict[str, Any]:
    payload = json.dumps({"token": token, "provider": "isa_user"}).encode("utf-8")
    verify_request = urlrequest.Request(
        f"{_auth_service_url(request)}/api/v1/auth/verify-token",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(verify_request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        return {"valid": False, "error": str(exc)}


def _as_values(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        raw_values = value.replace(";", ",").split(",")
    elif isinstance(value, dict):
        raw_values = [value.get("value"), value.get("role"), value.get("name")]
    else:
        try:
            raw_values = list(value)
        except TypeError:
            raw_values = [value]

    values: set[str] = set()
    for item in raw_values:
        if isinstance(item, dict):
            values.update(_as_values(item))
            continue
        if item is not None and str(item).strip():
            values.add(str(item).strip())
    return values


def _organization_values(value: Any) -> set[str]:
    if isinstance(value, dict):
        raw_values = [
            value.get("organization_id"),
            value.get("org_id"),
            value.get("id"),
        ]
        return {
            str(item).strip()
            for item in raw_values
            if item is not None and str(item).strip()
        }
    return _as_values(value)


def _training_roles(identity: dict[str, Any]) -> set[str]:
    roles = {
        role.lower()
        for key in ("role", "roles", "admin_roles", "org_role", "organization_role")
        for role in _as_values(identity.get(key))
    }
    permissions = {
        permission.lower()
        for key in ("permissions", "scopes")
        for permission in _as_values(identity.get(key))
    }
    if permissions.intersection({"training.admin", "training.org_admin"}):
        roles.add("org_admin")
    if "training.operator" in permissions:
        roles.add("operator")
    if permissions.intersection(
        {"training.review", "training.teacher", "training.parent"}
    ):
        roles.add("teacher")
    return roles


def _training_organizations(identity: dict[str, Any]) -> set[str]:
    return {
        org
        for key in (
            "organization_id",
            "organization_ids",
            "organizations",
            "org_id",
            "org_ids",
            "orgs",
        )
        for org in _organization_values(identity.get(key))
    }


def _bearer_identity(request: Request) -> dict[str, Any] | None:
    if hasattr(request.state, _IDENTITY_CACHE_KEY):
        return getattr(request.state, _IDENTITY_CACHE_KEY)

    token = _bearer_token(request)
    if not token:
        setattr(request.state, _IDENTITY_CACHE_KEY, None)
        return None

    identity = _verify_bearer_token(token, request)
    if not identity.get("valid") or not str(identity.get("user_id") or "").strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Training actions require a valid isA_User token.",
        )

    setattr(request.state, _IDENTITY_CACHE_KEY, identity)
    return identity


def require_user_id(request: Request) -> str:
    """Resolve the current user id from gateway-injected headers.

    The isA gateway and sibling services commonly pass both ``user-id`` and
    ``x-user-id``. This service accepts either form so local smoke tests and
    gateway-routed calls share the same contract.
    """
    identity = _bearer_identity(request)
    if identity is not None:
        return str(identity["user_id"]).strip()

    if _requires_gateway_verification(request) and not _gateway_verified(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Training actions require a verified isA gateway identity.",
        )

    user_id = request.headers.get("x-isa-user-id")
    if not _requires_gateway_verification(request):
        user_id = (
            user_id
            or request.headers.get("user-id")
            or request.headers.get("x-user-id")
        )

    if user_id and user_id.strip():
        return user_id.strip()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=AUTH_REQUIRED_DETAIL,
    )


def request_roles(request: Request) -> set[str]:
    identity = _bearer_identity(request)
    if identity is not None:
        return _training_roles(identity)

    raw_roles = request.headers.get("x-isa-roles") or ""
    if not _requires_gateway_verification(request):
        raw_roles = (
            request.headers.get("x-training-roles")
            or request.headers.get("x-user-roles")
            or raw_roles
            or request.headers.get("x-user-role")
            or ""
        )
    return {
        role.strip().lower()
        for role in raw_roles.replace(";", ",").split(",")
        if role.strip()
    }


def request_organizations(request: Request) -> set[str]:
    identity = _bearer_identity(request)
    if identity is not None:
        return _training_organizations(identity)

    raw_orgs = request.headers.get("x-isa-orgs") or ""
    if not _requires_gateway_verification(request):
        raw_orgs = (
            request.headers.get("x-training-orgs")
            or request.headers.get("x-user-orgs")
            or raw_orgs
            or request.headers.get("x-user-org")
            or ""
        )
    return {org.strip() for org in raw_orgs.replace(";", ",").split(",") if org.strip()}


def require_any_role(request: Request, allowed_roles: set[str]) -> set[str]:
    require_user_id(request)
    roles = request_roles(request)
    if roles.intersection(allowed_roles):
        return roles

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Training role required: {', '.join(sorted(allowed_roles))}",
    )


def require_organization_role(
    request: Request,
    organization_id: str,
    allowed_roles: set[str],
) -> set[str]:
    roles = require_any_role(request, allowed_roles)
    orgs = request_organizations(request)
    if not _requires_gateway_verification(request) and not orgs:
        return roles
    if organization_id in orgs:
        return roles

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Training organization access required: {organization_id}",
    )
