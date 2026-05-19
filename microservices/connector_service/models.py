"""
Connector Service Models

Pydantic v2 request/response shapes for the connector marketplace + custom
MCP routes. Aligns with the contract in
``docs/design/connector_marketplace_service.md`` and the ConnectorMarketplace
UI in isA_ (xenoISA/isA_#464).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# ============================================================================
# Catalog enums
# ============================================================================


class ConnectorAvailability(str, Enum):
    """Catalog-level availability for a built-in connector."""

    AVAILABLE = "available"
    BETA = "beta"
    DISABLED = "disabled"
    UNSUPPORTED = "unsupported"


class ConnectorAuthType(str, Enum):
    """Built-in connector auth handoff style."""

    OAUTH2 = "oauth2"
    API_KEY = "api_key"
    NONE = "none"
    CUSTOM = "custom"


class ConnectorInstallStatus(str, Enum):
    """Per-user install state for a built-in connector."""

    CONNECTED = "connected"
    PENDING_AUTH = "pending_auth"
    ERROR = "error"
    DISCONNECTED = "disconnected"


# ============================================================================
# Custom MCP enums
# ============================================================================


class CustomMcpAuthKind(str, Enum):
    """Authentication for a user-added remote MCP server.

    ``oauth_oob`` is "out-of-band" OAuth — the user pastes the token they
    already obtained from the upstream MCP host. We do NOT run an OAuth
    dance ourselves in this slice.
    """

    NONE = "none"
    PAT = "pat"
    OAUTH_OOB = "oauth_oob"


class CustomMcpStatus(str, Enum):
    """Lifecycle of a custom MCP connector row."""

    PENDING = "pending"
    ACTIVE = "active"
    ERROR = "error"
    REVOKED = "revoked"


# ============================================================================
# Catalog response shapes — match docs/design/connector_marketplace_service.md
# and the `Connector` type the frontend ConnectorMarketplace renders.
# ============================================================================


class ConnectorCatalogItem(BaseModel):
    """Built-in connector catalog row."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Stable provider id, e.g. google_calendar")
    name: str
    description: str
    icon: Optional[str] = None
    category: str = Field(
        ..., description="calendar | storage | crm | email | productivity | custom"
    )
    auth_type: ConnectorAuthType
    capabilities: List[str] = Field(default_factory=list)
    availability: ConnectorAvailability = ConnectorAvailability.AVAILABLE
    provider_metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConnectorCatalogResponse(BaseModel):
    """GET /api/v1/connectors/catalog response."""

    connectors: List[ConnectorCatalogItem]
    count: int


# ============================================================================
# Installed (per-user) shapes
# ============================================================================


class ConnectorInstallState(BaseModel):
    """Per-user install record for a built-in connector."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str
    connector_id: str
    status: ConnectorInstallStatus
    auth_url: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    scopes: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CustomMcpConnector(BaseModel):
    """User-added remote MCP connector row (sans secret)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    label: str
    url: str
    auth_kind: CustomMcpAuthKind
    status: CustomMcpStatus
    last_error: Optional[str] = None
    created_at: Optional[datetime] = None
    last_validated_at: Optional[datetime] = None
    last_handshake_at: Optional[datetime] = None
    tools_count: Optional[int] = Field(
        None,
        description="Number of tools returned by the most recent successful handshake",
    )


class InstalledConnectorsResponse(BaseModel):
    """GET /api/v1/connectors/installed response.

    The frontend merges ``installed`` (per-user state on built-in catalog
    items) with ``custom`` (BYO remote MCP rows) when rendering the
    marketplace's "My connectors" view.
    """

    installed: List[ConnectorInstallState] = Field(default_factory=list)
    custom: List[CustomMcpConnector] = Field(default_factory=list)
    count: int


# ============================================================================
# Custom MCP request shapes
# ============================================================================


class CreateCustomMcpRequest(BaseModel):
    """POST /api/v1/connectors/custom body."""

    label: str = Field(
        ..., min_length=1, max_length=120, description="Display label, user-supplied"
    )
    url: HttpUrl = Field(
        ..., description="Remote MCP server endpoint (https:// preferred)"
    )
    auth_kind: CustomMcpAuthKind = CustomMcpAuthKind.NONE
    auth_secret: Optional[str] = Field(
        None,
        description=(
            "Bearer token / PAT — required when auth_kind != none. Stored in vault, never returned in responses."
        ),
        min_length=1,
        max_length=4096,
    )


# ============================================================================
# Error / handshake response shapes
# ============================================================================


class ConnectorErrorBody(BaseModel):
    """Error envelope for connector_service — matches design contract.

    Returned as ``{"error": ConnectorErrorBody}`` on non-2xx responses so
    callers can switch on a stable machine code.
    """

    code: str
    message: str


class HandshakeFailure(BaseModel):
    """422 body when the MCP handshake fails during POST /custom or /revalidate."""

    error: ConnectorErrorBody
