"""Shared request/response schemas for auth_service."""

from typing import List, Optional

from pydantic import BaseModel, Field


class OAuthClientCreateRequest(BaseModel):
    """OAuth client creation request."""

    client_name: str = Field(..., description="Human-readable client name")
    organization_id: Optional[str] = Field(None, description="Owning organization ID")
    allowed_scopes: List[str] = Field(
        default_factory=lambda: ["mcp:tools:execute"],
        description="Allowed OAuth scopes for this client",
    )
    token_ttl_seconds: int = Field(
        3600, ge=300, le=86400, description="Access token TTL in seconds"
    )
    client_type: str = Field("confidential", description="OAuth client type")
    redirect_uris: List[str] = Field(
        default_factory=list, description="Allowed authorization-code redirect URIs"
    )
    require_pkce: bool = Field(
        True, description="Whether authorization-code requests must use PKCE"
    )
