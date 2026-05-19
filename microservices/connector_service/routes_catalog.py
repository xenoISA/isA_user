"""
Connector catalog routes — GET /api/v1/connectors/catalog.

The catalog is currently SEED-only: a YAML file under
``data/builtin_catalog.yaml`` is loaded once on import and served as the
authoritative built-in connector list. Per the contract in
``docs/design/connector_marketplace_service.md`` this is also where
``?category=`` / ``?availability=`` filters would land — we expose
``category`` filtering today and leave the rest for a follow-up.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import yaml
from fastapi import APIRouter, Query

from .models import (
    ConnectorAvailability,
    ConnectorCatalogItem,
    ConnectorCatalogResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/connectors", tags=["connector-catalog"])

_CATALOG_PATH = Path(__file__).parent / "data" / "builtin_catalog.yaml"


def _load_catalog() -> List[ConnectorCatalogItem]:
    """Read the YAML seed catalog into validated Pydantic models.

    Loaded at import time (not per-request) — the catalog is static for
    the lifetime of the service. The seed file ships with the image, so
    parse failures are programmer errors and we let them bubble up as
    a startup crash rather than silently serving an empty catalog.
    """
    raw = yaml.safe_load(_CATALOG_PATH.read_text())
    items = raw.get("connectors", []) if isinstance(raw, dict) else []
    now = datetime.now(timezone.utc)
    catalog: List[ConnectorCatalogItem] = []
    for entry in items:
        # Stamp created_at/updated_at if the YAML didn't provide them —
        # the contract requires both to be present.
        entry.setdefault("created_at", now)
        entry.setdefault("updated_at", now)
        catalog.append(ConnectorCatalogItem.model_validate(entry))
    logger.info("connector catalog loaded: %d entries", len(catalog))
    return catalog


_CATALOG: List[ConnectorCatalogItem] = _load_catalog()


def _filter(
    items: List[ConnectorCatalogItem],
    *,
    category: Optional[str],
    include_disabled: bool,
) -> List[ConnectorCatalogItem]:
    """Apply optional ?category= and ?include_disabled= filters."""
    out = items
    if category:
        cat = category.lower().strip()
        out = [i for i in out if i.category.lower() == cat]
    if not include_disabled:
        out = [
            i
            for i in out
            if i.availability
            not in (ConnectorAvailability.DISABLED, ConnectorAvailability.UNSUPPORTED)
        ]
    return out


@router.get("/catalog", response_model=ConnectorCatalogResponse)
async def list_catalog(
    category: Optional[str] = Query(None, description="Filter by category"),
    include_disabled: bool = Query(
        False, description="Include disabled/unsupported connectors"
    ),
) -> ConnectorCatalogResponse:
    """Return the built-in connector catalog.

    Public-by-default in terms of "every authenticated user sees the
    same rows" — the catalog itself isn't per-user. APISIX still
    enforces JWT.
    """
    filtered = _filter(_CATALOG, category=category, include_disabled=include_disabled)
    return ConnectorCatalogResponse(connectors=filtered, count=len(filtered))


def get_catalog_snapshot() -> List[ConnectorCatalogItem]:
    """Test helper: return a copy of the in-memory catalog."""
    return list(_CATALOG)
